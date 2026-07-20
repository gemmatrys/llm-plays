# Launch mGBA for the harness: Game Boy Color model, no Super Game Boy border.
# The Lua bridge still needs one manual step after launch (mGBA 0.10.x has no
# --script CLI): Tools -> Scripting... -> File -> Load script... ->
#   emulator\mgba_bridge.lua   (console prints: bridge listening on port 8765)
param(
    [string]$Rom = "D:\workspace_claude\resources\roms\Pokemon - Red Version (USA, Europe).gb",
    [string]$MGBA = "C:\Program Files\mGBA\mGBA.exe"
)

if (-not (Test-Path $MGBA)) { throw "mGBA not found at $MGBA" }
if (-not (Test-Path $Rom)) { throw "ROM not found at $Rom" }

# -C overrides beat the GUI config: CGB model = proper GBC palette, no SGB
# border, so the harness always sees native 160x144 game pixels
& $MGBA -C gb.model=CGB -C sgb.borders=0 $Rom

Write-Host "mGBA launched (CGB, borderless): $(Split-Path $Rom -Leaf)"
Write-Host "REMINDER: load emulator\mgba_bridge.lua via Tools -> Scripting"
