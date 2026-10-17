#!/usr/bin/env python3
"""Run a bundled upstream Game Boy CPU diagnostic ROM through serial output."""

import argparse
import os
import selectors
import signal
import subprocess
import sys
import time


def run_rom(binary, rom, marker, timeout_seconds):
    env = os.environ.copy()
    env["SDL_VIDEODRIVER"] = "dummy"
    env["SDL_AUDIODRIVER"] = "dummy"
    command = [binary, "--fullspeed", "--nosound", rom]
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        bufsize=0,
    )
    output = bytearray()
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    deadline = time.monotonic() + timeout_seconds
    success_marker = marker.lower().encode("ascii")

    try:
        while time.monotonic() < deadline:
            if process.poll() is not None:
                break
            for key, _ in selector.select(timeout=0.25):
                chunk = os.read(key.fileobj.fileno(), 4096)
                if not chunk:
                    continue
                output.extend(chunk)
                normalized = bytes(output).lower()
                if b"failed" in normalized or b"failure" in normalized:
                    raise RuntimeError("upstream ROM reported a failure")
                if success_marker in normalized:
                    process.send_signal(signal.SIGTERM)
                    process.wait(timeout=5)
                    print("[PASS] {}: observed {!r}".format(rom, marker))
                    return bytes(output)
        raise RuntimeError(
            "did not observe {!r} within {} seconds".format(marker, timeout_seconds)
        )
    except Exception:
        if process.poll() is None:
            process.kill()
        process.wait()
        rendered = bytes(output).decode("latin-1", errors="replace")
        print(rendered[-6000:], file=sys.stderr)
        raise
    finally:
        selector.close()
        if process.stdout is not None:
            process.stdout.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", required=True)
    parser.add_argument("--rom-root", required=True)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--log", required=True)
    args = parser.parse_args()

    roms = [
        (
            os.path.join(args.rom_root, "cpu_instrs", "individual", "01-special.gb"),
            "passed",
        ),
    ]
    with open(args.log, "wb") as log_file:
        for rom, marker in roms:
            output = run_rom(args.binary, rom, marker, args.timeout)
            log_file.write("===== {} =====\n".format(rom).encode("utf-8"))
            log_file.write(output)
            log_file.write(b"\n")
            log_file.flush()
    print("Executed {} upstream ROM suites.".format(len(roms)))


if __name__ == "__main__":
    main()
