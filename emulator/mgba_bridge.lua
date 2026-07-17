-- mgba_bridge.lua — TCP control bridge for the llm-plays harness.
-- Load in mGBA (>= 0.10): Tools -> Scripting -> Load script.
-- Serves the line protocol documented in harness/drivers/mgba.py on port 8765.
--
-- NOTE: scaffold — written against the mGBA 0.10 scripting API
-- (https://mgba.io/docs/scripting.html); verify callback/API names in Phase 0.

local PORT = 8765

-- GBA/GB key indices per mGBA C.GBA_KEY ordering
local KEYS = {
  A = 0, B = 1, SELECT = 2, START = 3,
  RIGHT = 4, LEFT = 5, UP = 6, DOWN = 7, R = 8, L = 9,
}

local held = {}          -- key index -> frames remaining (-1 = until UP command)
local server = nil
local sockets = {}
local nextID = 1

-- Apply held keys every frame; frame-timed holds regardless of harness latency.
callbacks:add("frame", function()
  local mask = 0
  for key, frames in pairs(held) do
    if frames == -1 then          -- held down until an UP command clears it
      mask = mask | (1 << key)
    elseif frames > 0 then
      mask = mask | (1 << key)
      held[key] = frames - 1
    else
      held[key] = nil
    end
  end
  emu:setKeys(mask)
end)

local function handle(line)
  local args = {}
  for w in line:gmatch("%S+") do args[#args + 1] = w end
  local cmd = (args[1] or ""):upper()

  if cmd == "PING" then
    return "OK PONG"
  elseif cmd == "PRESS" then
    local key = KEYS[(args[2] or ""):upper()]
    local frames = tonumber(args[3]) or 8
    if key == nil then return "ERR unknown button" end
    held[key] = frames
    return "OK"
  elseif cmd == "DOWN" then
    local key = KEYS[(args[2] or ""):upper()]
    if key == nil then return "ERR unknown button" end
    held[key] = -1
    return "OK"
  elseif cmd == "UP" then
    local key = KEYS[(args[2] or ""):upper()]
    if key == nil then return "ERR unknown button" end
    held[key] = nil
    return "OK"
  elseif cmd == "SCREENSHOT" then
    if not args[2] then return "ERR missing path" end
    emu:screenshot(args[2])
    return "OK " .. args[2]
  elseif cmd == "READ8" then
    local addr = tonumber(args[2])
    if addr == nil then return "ERR bad address" end
    return "OK " .. tostring(emu:read8(addr))
  elseif cmd == "SAVESTATE" then
    emu:saveStateSlot(tonumber(args[2]) or 1)
    return "OK"
  elseif cmd == "LOADSTATE" then
    emu:loadStateSlot(tonumber(args[2]) or 1)
    return "OK"
  elseif cmd == "RESET" then
    emu:reset()
    return "OK"
  else
    return "ERR unknown command"
  end
end

local function socketReceived(id)
  local sock = sockets[id]
  if not sock then return end
  while true do
    local line, err = sock:receive(1024)
    if line then
      for l in line:gmatch("[^\r\n]+") do
        local ok, reply = pcall(handle, l)
        sock:send((ok and reply or ("ERR " .. tostring(reply))) .. "\n")
      end
    else
      if err ~= socket.ERRORS.AGAIN then
        sock:close()
        sockets[id] = nil
      end
      return
    end
  end
end

local function socketAccept()
  local sock, err = server:accept()
  if err then return end
  local id = nextID
  nextID = nextID + 1
  sockets[id] = sock
  sock:add("received", function() socketReceived(id) end)
  sock:add("error", function() sockets[id] = nil end)
end

server = socket.bind(nil, PORT)
if server then
  server:add("received", socketAccept)
  server:listen()
  console:log("llm-plays bridge listening on port " .. PORT)
else
  console:error("llm-plays bridge: could not bind port " .. PORT)
end
