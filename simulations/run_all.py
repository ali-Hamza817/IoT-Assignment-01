"""Run every simulation in order and regenerate all videos, GIF previews, charts and results."""
import subprocess
import sys
import time
from pathlib import Path

SCRIPTS = ["q1_grid_deployment.py", "q2_rts_cts.py", "q3_forest_fire_wsn.py"]


def main():
    here = Path(__file__).resolve().parent
    for script in SCRIPTS:
        start = time.time()
        print(f"=== {script}", flush=True)
        subprocess.run([sys.executable, script], cwd=here, check=True)
        print(f"=== {script} finished in {time.time() - start:.0f} s", flush=True)


if __name__ == "__main__":
    main()
