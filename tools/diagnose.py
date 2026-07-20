import json
import sys
from pathlib import Path

sys.path.insert(0, r"D:\workspace_claude\llm-plays")
RUN = Path(r"D:\workspace_claude\llm-plays\runs\pokemon_red\gemma-run-1")

lines = RUN.joinpath("log.jsonl").read_text(encoding="utf-8").splitlines()
print(f"total decisions: {len(lines)}")
for raw in lines[-10:]:
    e = json.loads(raw)
    plan = f" plan{len(e['plan'])}/{e.get('executed')}" if "plan" in e else ""
    print(f"{e.get('rung')}|{e.get('behavior')}{plan} "
          f"pos=({e['ram'].get('pos_x')},{e['ram'].get('pos_y')}) "
          f"map={e['ram'].get('map_id')} — {e.get('reason', '')[:70]}")
print("--- notes:", RUN.joinpath("memory.md").read_text(encoding="utf-8"))

from harness.drivers.mgba import MGBADriver
d = MGBADriver()
d.connect()
d.get_frame().image.save(
    r"C:\Users\bear0\AppData\Local\Temp\claude\D--workspace-claude"
    r"\1e808159-e427-40db-a169-68ccb0d80641\scratchpad\stuck_now.png")
print("frame saved")
