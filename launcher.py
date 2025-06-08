import argparse
import subprocess
import sys
import threading
import time
from typing import List


def stream_output(proc: subprocess.Popen, label: str, buffer: List[str]):
    """Forward process output to the terminal while storing it."""
    try:
        for line in iter(proc.stdout.readline, ''):
            if not line:
                break
            buffer.append(line)
            print(f"[{label}] {line}", end='')
    except Exception as exc:
        print(f"[!] Error reading {label} output: {exc}")


def start_process(cmd: List[str], label: str):
    """Start a subprocess and stream its output."""
    buffer: List[str] = []
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        thread = threading.Thread(target=stream_output, args=(proc, label, buffer), daemon=True)
        thread.start()
        print(f"[✓] {label} launched successfully.")
        return proc, buffer
    except FileNotFoundError as exc:
        print(f"[!] Failed to start {label}: {exc}")
        return None, buffer


def main():
    parser = argparse.ArgumentParser(description="Launch trading bot and dashboard")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--simulate", action="store_true", help="Run bot in simulation mode")
    mode_group.add_argument("--live", action="store_true", help="Run bot in live trading mode")
    args = parser.parse_args()

    bot_cmd = [sys.executable, "main.py"]
    if args.simulate:
        bot_cmd.append("--simulate")
    elif args.live:
        bot_cmd.append("--live")

    bot_proc, bot_buffer = start_process(bot_cmd, "Bot")
    dash_proc, dash_buffer = start_process(["streamlit", "run", "dashboard/app.py"], "Dashboard")

    if dash_proc:
        print("[✓] Dashboard running at http://localhost:8501")

    try:
        while True:
            time.sleep(1)
            if bot_proc and bot_proc.poll() is not None:
                err = ''.join(bot_buffer[-10:]).strip()
                msg = f"[!] Bot crashed with error: {err}" if err else f"[!] Bot exited with code {bot_proc.returncode}"
                print(msg)
                break
            if dash_proc and dash_proc.poll() is not None:
                err = ''.join(dash_buffer[-10:]).strip()
                msg = f"[!] Dashboard crashed with error: {err}" if err else f"[!] Dashboard exited with code {dash_proc.returncode}"
                print(msg)
                break
    except KeyboardInterrupt:
        print("\n[!] Interrupt received. Shutting down...")
    finally:
        for proc, label in [(bot_proc, "Bot"), (dash_proc, "Dashboard")]:
            if proc and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                print(f"[✓] {label} terminated.")


if __name__ == "__main__":
    main()
