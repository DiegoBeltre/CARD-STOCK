import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def main():
    sites = ["walmart", "pokemoncenter"]
    processes = {}

    for site in sites:
        processes[site] = start_process(site)

    try:
        while True:
            for site in sites:
                process = processes[site]
                if process.poll() is not None:
                    print(f"{site} exited with code {process.returncode}; restarting...")
                    processes[site] = start_process(site)
            time.sleep(5)
    except KeyboardInterrupt:
        print("Stopping all scraper processes...")
        for process in processes.values():
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
        print("All scraper processes stopped.")


def start_process(site: str):
    command = [sys.executable, str(BASE_DIR / "main.py"), site]
    process = subprocess.Popen(
        command,
        cwd=str(BASE_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    print(f"Started {site} with PID {process.pid}")
    return process


if __name__ == "__main__":
    main()
