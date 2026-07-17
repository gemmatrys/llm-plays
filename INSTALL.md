# Installation Guide — inference server + harness machine

Two machines (or two roles on one machine):

- **Inference server**: the Arc Pro B70 box. Serves an OpenAI-compatible API on the LAN.
- **Harness machine**: runs the emulator + harness (any OS; currently the Windows
  workstation). Talks to the server over HTTP. Phase 6 adds the capture card + Pico here.

---

## 1. Inference server

### Recommended: Ubuntu 26.04 LTS + Docker + Intel LLM-Scaler vLLM  ✅

Why this combo:
- Ubuntu 26.04 supports Battlemage natively: Xe kernel driver (kernel 7.0), Mesa 26,
  Intel Compute Runtime and DPC++ available straight from the Ubuntu archive.
- Docker keeps the fragile oneAPI userspace inside Intel's container; the host only
  needs the kernel driver and container runtime. OS upgrades can't break inference.
- `intel/llm-scaler-vllm` is Intel's officially supported vLLM line for Arc Pro
  B-series (B70 support since 0.14.0-b8.2), and adds INT4/FP8 online quantization that
  upstream vLLM XPU lacks.

Steps:

```bash
# 1. Install Ubuntu 26.04 LTS Server (minimal). During install: OpenSSH server.

# 2. Verify the GPU is bound to the xe driver
lspci -k | grep -A3 -i vga         # expect: Kernel driver in use: xe
ls /dev/dri                        # expect: card0/renderD128 (numbers may vary)

# 3. Host GPU userspace (for sanity checks like `clinfo`; containers ship their own)
sudo apt install intel-opencl-icd clinfo
clinfo | grep "Device Name"        # expect the B70

# 4. Docker
sudo apt install docker.io
sudo usermod -aG docker,render $USER   # re-login after this

# 5. Pull and run the serving container (check llm-scaler README for current tag)
docker pull intel/llm-scaler-vllm:latest
docker run -d --name vllm --restart unless-stopped \
  --device /dev/dri --group-add render --shm-size 8g \
  -v /opt/models:/models -p 8000:8000 \
  intel/llm-scaler-vllm:latest \
  serve google/gemma-3-27b-it --port 8000 \
  --max-model-len 8192 --quantization <int4|fp8, per llm-scaler docs>
```

Acceptance tests (these are PLAN §7.1 — run all five before Phase 2):

```bash
# text
curl http://SERVER:8000/v1/chat/completions -H 'Content-Type: application/json' -d \
 '{"model":"google/gemma-3-27b-it","messages":[{"role":"user","content":"say hi"}]}'

# vision: send a base64 game screenshot in an image_url content part
# structured output: pass "response_format": {"type":"json_schema", ...} (vLLM guided
#   decoding) and verify a schema-violating output is impossible
# latency: time a vision request end-to-end -> sets decision cadence in game profiles
```

Notes / current bugs to respect:
- **Single GPU only for now**: open upstream bugs for both vision models on multi-Arc
  (IPEX-LLM #13318) and TP=2 on dual B70 (vLLM #41663). One B70 sidesteps both.
- Verify guided/structured decoding works in the XPU container early — if it doesn't,
  fall back to strict prompt + validator + retry inside the harness (rung-1 trust
  condition already handles rejection).

### Alternative A: IPEX-LLM Ollama (bare metal)

Simpler mental model (one binary, `ollama run`), but **currently broken on 26.04**
(oneAPI runner fails to install — ollama/ollama #15827) and the vision-model story on
Arc has open crashes. Viable on Ubuntu 24.04 if the Docker route disappoints. Not
recommended as the primary path.

### Alternative B: llama.cpp Vulkan

No oneAPI stack at all — plain Vulkan, works on Mesa out of the box, supports Gemma 3
vision (mtmd) and GBNF grammars (strongest structured-output guarantee of the three).
Slower than vLLM, single-request oriented. Keep as the break-glass fallback; zero setup
risk, so no pre-work needed.

---

## 2. Harness machine (Phase 0–5: emulator era)

Current workstation (Windows) is fine — the harness is pure Python + TCP.

1. **mGBA ≥ 0.10.x** (https://mgba.io) — needs the Lua scripting console
   (Tools → Scripting). BizHawk is the fallback if mGBA scripting proves limiting.
2. **Python ≥ 3.11**, then from the repo root:
   ```
   pip install -e .
   ```
3. **ROMs**: dumps of cartridges you own, outside the repo (path goes in the game
   profile).
4. Run mGBA, load ROM, load `emulator/mgba_bridge.lua` in the scripting console, then:
   ```
   python -m harness --profile profiles/pokemon_red.yaml --policy fish
   ```

Phase 6 additions (Switch era, buy later): HDMI USB3 capture device, Raspberry Pi Pico
flashed as a wired Pro Controller, HDMI splitter. Eyes/Hands get new drivers; nothing
else changes.
