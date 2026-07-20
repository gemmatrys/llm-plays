"""PLAN 7.1 validation checklist against the Arc box vLLM server.

Run from the harness machine (same network position the real harness has):
1. text generation works
2. vision request works (synthetic Game Boy-ish frame)
3. constrained JSON output is enforced (schema-invalid output impossible)
4. latency with an image in the prompt -> sets the decision cadence
"""
import base64
import io
import json
import time

import requests
from PIL import Image, ImageDraw

BASE = "http://192.168.1.30:8000"
MODEL = "gemma"


def frame_data_url() -> str:
    # synthetic GB-like frame: 160x144, 4-shade green palette, dialogue box
    img = Image.new("RGB", (160, 144), (155, 188, 15))
    d = ImageDraw.Draw(img)
    d.rectangle([4, 100, 156, 140], fill=(15, 56, 15))
    d.rectangle([6, 102, 154, 138], outline=(155, 188, 15))
    d.text((12, 108), "PROF.OAK: Hello there!", fill=(155, 188, 15))
    d.text((12, 122), "Welcome to POKEMON!", fill=(155, 188, 15))
    d.rectangle([70, 40, 90, 70], fill=(48, 98, 48))  # a "character"
    img = img.resize((480, 432), Image.NEAREST)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def chat(messages, timeout=180, **kw):
    t0 = time.time()
    r = requests.post(f"{BASE}/v1/chat/completions", timeout=timeout, json={
        "model": MODEL, "messages": messages, "max_tokens": 200, **kw})
    dt = time.time() - t0
    r.raise_for_status()
    j = r.json()
    return j["choices"][0]["message"]["content"], dt, j.get("usage", {})


def main():
    # 1. text
    text, dt, usage = chat([{"role": "user", "content":
                             "Reply with exactly: HARNESS TEXT OK"}])
    print(f"1. text OK ({dt:.1f}s): {text.strip()[:60]!r}")

    # 2. vision
    vision_msg = [{"role": "user", "content": [
        {"type": "text", "text": "Describe this Game Boy screen in one sentence. "
                                 "What text is shown?"},
        {"type": "image_url", "image_url": {"url": frame_data_url()}},
    ]}]
    desc, dt, usage = chat(vision_msg)
    print(f"2. vision OK ({dt:.1f}s): {desc.strip()[:120]!r}")

    # 3. constrained JSON (the harness's actual schema shape)
    schema = {
        "type": "object",
        "properties": {
            "plan": {"type": "array",
                     "items": {"type": "string",
                               "enum": ["press_A", "press_UP", "mash_a"]},
                     "minItems": 1, "maxItems": 8},
            "why": {"type": "string", "maxLength": 100},
        },
        "required": ["plan"], "additionalProperties": False,
    }
    content, dt, usage = chat(
        [{"role": "user", "content": [
            {"type": "text", "text": "You control this game. Choose a plan of "
             "behaviors from: press_A, press_UP, mash_a."},
            {"type": "image_url", "image_url": {"url": frame_data_url()}}]}],
        response_format={"type": "json_schema",
                         "json_schema": {"name": "plan", "schema": schema}})
    action = json.loads(content)
    assert isinstance(action["plan"], list) and 1 <= len(action["plan"]) <= 8
    assert all(b in ("press_A", "press_UP", "mash_a") for b in action["plan"])
    print(f"3. constrained JSON OK ({dt:.1f}s): {action}")

    # 4. latency: 3 vision+schema decisions, the harness's real workload
    times, toks = [], []
    for _ in range(3):
        _, dt, usage = chat(
            [{"role": "user", "content": [
                {"type": "text", "text": "Choose a plan from: press_A, press_UP, "
                 "mash_a. One short why."},
                {"type": "image_url", "image_url": {"url": frame_data_url()}}]}],
            response_format={"type": "json_schema",
                             "json_schema": {"name": "plan", "schema": schema}})
        times.append(dt)
        toks.append(usage.get("completion_tokens", 0))
    avg = sum(times) / len(times)
    print(f"4. latency: {[f'{t:.1f}s' for t in times]} avg={avg:.1f}s "
          f"(completion tokens {toks})")
    print(f"   -> suggested decision_cadence_s >= {avg:.0f}s; "
          f"plan-of-8 amortizes to ~{avg/8:.1f}s/action")
    print("ALL SERVER VALIDATION PASSED")


if __name__ == "__main__":
    main()
