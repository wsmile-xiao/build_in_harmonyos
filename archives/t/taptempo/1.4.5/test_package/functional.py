"""Run TapTempo as a packaged program and exercise its observable CLI behavior."""

import argparse
import json
import math
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path


TEMPO = re.compile(r"Tempo:\s+([0-9]+(?:\.[0-9]+)?) bpm")


def invoke(binary, args=(), delays=None, end="q"):
    env = None
    if os.name != "nt":
        env = os.environ.copy()
        env["LC_ALL"] = "C"
    started = time.monotonic()
    proc = subprocess.Popen([str(binary), *args], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    beats = []
    try:
        if delays is not None:
            for delay in delays:
                sleep_started = time.monotonic_ns()
                time.sleep(delay)
                sleep_seconds = (time.monotonic_ns() - sleep_started) / 1e9
                proc.stdin.write(b"\n")
                proc.stdin.flush()
                beats.append({"requested_delay_seconds": delay,
                              "actual_sleep_seconds": round(sleep_seconds, 6),
                              "sent_monotonic_ns": time.monotonic_ns()})
            if end == "q":
                proc.stdin.write(b"q\n")
                proc.stdin.flush()
        proc.stdin.close()
        proc.stdin = None
        stdout, stderr = proc.communicate(timeout=12)
    except (BrokenPipeError, subprocess.TimeoutExpired):
        proc.kill()
        stdout, stderr = proc.communicate()
    return {
        "args": list(args),
        "delays_seconds": delays,
        "beats": beats,
        "stdin_end": end,
        "returncode": proc.returncode,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "stdout": stdout.decode("utf-8", "replace"),
        "stderr": stderr.decode("utf-8", "replace"),
    }


def invoke_synced(binary, args, delays, responses):
    """Acknowledge each beat before scheduling the next one.

    TapTempo flushes its prompt and per-beat output before reading the next
    input. For each beat, the target consumption time is bounded by the
    writer's send start and the reader's acknowledgement of its output.
    """
    ensure(len(delays) == len(responses), "beat/response count mismatch")
    env = None
    if os.name != "nt":
        env = os.environ.copy()
        env["LC_ALL"] = "C"
    started = time.monotonic()
    proc = subprocess.Popen([str(binary), *args], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    output = bytearray()
    condition = threading.Condition()
    beats = []
    sync_error = None

    def read_stdout():
        while True:
            chunk = proc.stdout.read(1)
            if not chunk:
                break
            with condition:
                output.extend(chunk)
                condition.notify_all()

    def wait_for(marker, count=1, timeout=8):
        deadline = time.monotonic() + timeout
        with condition:
            while output.count(marker) < count:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
                condition.wait(remaining)
        return time.monotonic_ns()

    reader = threading.Thread(target=read_stdout, daemon=True)
    reader.start()
    try:
        if wait_for(b"Hit enter key for each beat") is None:
            sync_error = "initial prompt was not flushed"
        else:
            for delay, (marker, count) in zip(delays, responses):
                sleep_started = time.monotonic_ns()
                time.sleep(delay)
                sleep_seconds = (time.monotonic_ns() - sleep_started) / 1e9
                send_started = time.monotonic_ns()
                proc.stdin.write(b"\n")
                proc.stdin.flush()
                sent = time.monotonic_ns()
                acknowledged = wait_for(marker, count)
                beats.append({"requested_delay_seconds": delay,
                              "actual_sleep_seconds": round(sleep_seconds, 6),
                              "send_started_ns": send_started,
                              "sent_monotonic_ns": sent,
                              "ack_monotonic_ns": acknowledged,
                              "response": marker.decode("ascii"),
                              "response_count": count})
                if acknowledged is None:
                    sync_error = f"no flushed response after beat {len(beats)}"
                    break
        if proc.poll() is None:
            proc.stdin.write(b"q\n")
            proc.stdin.flush()
        proc.stdin.close()
        proc.stdin = None
        proc.wait(timeout=12)
    except (BrokenPipeError, OSError, subprocess.TimeoutExpired) as exc:
        sync_error = f"{type(exc).__name__}: {exc}"
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        reader.join(timeout=2)
    return {"args": list(args), "delays_seconds": list(delays),
            "beats": beats, "sync_error": sync_error,
            "returncode": proc.returncode,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "stdout": bytes(output).decode("utf-8", "replace"),
            "stderr": proc.stderr.read().decode("utf-8", "replace")}


def bpm_values(result):
    return [float(x) for x in TEMPO.findall(result["stdout"])]


def ensure(condition, message):
    if not condition:
        raise AssertionError(message)


def ensure_tempo_matches_beat_bounds(result, actual_bpm, intervals):
    """Check BPM against consumption-time bounds from each beat's output."""
    beats = result["beats"]
    ensure(len(beats) > intervals, "not enough acknowledged beats")
    first, last = beats[-1 - intervals], beats[-1]
    ensure(first["ack_monotonic_ns"] is not None and
           last["ack_monotonic_ns"] is not None, "missing beat acknowledgement")
    shortest = (last["send_started_ns"] - first["ack_monotonic_ns"]) / 1e9
    longest = (last["ack_monotonic_ns"] - first["send_started_ns"]) / 1e9
    ensure(shortest > 0 and longest >= shortest,
           "invalid target consumption interval bounds")
    lower_bpm = 60.0 * intervals / longest
    upper_bpm = 60.0 * intervals / shortest
    # Integer CLI output rounds BPM; half a unit covers display rounding.
    ensure(lower_bpm - 0.51 <= actual_bpm <= upper_bpm + 0.51,
           f"observed {actual_bpm} BPM outside consumption bounds "
           f"[{lower_bpm:.2f}, {upper_bpm:.2f}] from {intervals} intervals")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("binary", type=Path)
    parser.add_argument("--report-dir", type=Path, required=True)
    args = parser.parse_args()
    args.report_dir.mkdir(parents=True, exist_ok=True)
    results = []
    observed_runs = []

    def run(*run_args, **run_kwargs):
        result = invoke(*run_args, **run_kwargs)
        observed_runs.append(result)
        return result

    def run_synced(*run_args, **run_kwargs):
        result = invoke_synced(*run_args, **run_kwargs)
        observed_runs.append(result)
        return result

    def check(name, action):
        observed_runs.clear()
        entry = {"name": name, "passed": False}
        try:
            action()
            entry["passed"] = True
        except Exception as exc:
            entry["error"] = f"{type(exc).__name__}: {exc}"
        entry["runs"] = list(observed_runs)
        results.append(entry)
        print(f"{'PASS' if entry['passed'] else 'FAIL'} {name}", flush=True)

    def version():
        r = run(args.binary, ("--version",), end="eof")
        ensure(r["returncode"] == 0, "--version exit status")
        ensure("Tap Tempo 1.4.5" in r["stdout"], "version text")
        return [r]

    def help_text():
        r = run(args.binary, ("--help",), end="eof")
        ensure(r["returncode"] == 0, "--help exit status")
        ensure("Usage: taptempo [options]" in r["stdout"], "usage text")
        ensure("--sample-size" in r["stdout"], "option text")
        return [r]

    def invalid_option():
        r = run(args.binary, ("--bogus",), end="eof")
        ensure(r["returncode"] == 0, "upstream invalid option status changed")
        ensure(r["stderr"].strip(), "getopt error text missing")
        ensure("Hit enter key" not in r["stdout"], "invalid option entered loop")
        return [r]

    def quit_key():
        r = run(args.binary, delays=[], end="q")
        ensure(r["returncode"] == 0, "q exit status")
        ensure("Bye Bye!" in r["stdout"], "q did not exit")
        return [r]

    def eof_exit():
        r = run(args.binary, delays=[], end="eof")
        ensure(r["returncode"] == 0, "EOF exit status")
        ensure("Bye Bye!" in r["stdout"], "EOF did not exit")
        return [r]

    def measured_tempo():
        r = run_synced(args.binary, ("-p", "2"), [0.0, 0.5, 0.5],
                       [(b"one more time", 1), (b"Tempo:", 1),
                        (b"Tempo:", 2)])
        values = bpm_values(r)
        ensure(r["sync_error"] is None, f"tempo synchronization: {r['sync_error']}")
        ensure(r["returncode"] == 0, "tempo exit status")
        ensure(len(values) >= 2, "two timed BPM results missing")
        ensure(all(math.isfinite(value) and value > 0 for value in values),
               f"invalid BPM output: {values}")
        ensure_tempo_matches_beat_bounds(r, values[-1], 2)
        ensure(re.search(r"Tempo:\s+\d+\.\d{2} bpm", r["stdout"]),
               "two-digit precision missing")
        return [r]

    def precision_clamp():
        r = run_synced(args.binary, ("-p", "99"), [0.0, 0.5],
                       [(b"one more time", 1), (b"Tempo:", 1)])
        ensure(r["sync_error"] is None, f"precision synchronization: {r['sync_error']}")
        ensure(r["returncode"] == 0, "precision clamp exit status")
        ensure(re.search(r"Tempo:\s+\d+\.\d{5} bpm", r["stdout"]),
               "precision not clamped to five digits")
        return [r]

    def sample_window():
        responses = [(b"one more time", 1), (b"Tempo:", 1),
                     (b"Tempo:", 2)]
        one = run_synced(args.binary, ("-s", "1"), [0.0, 0.5, 1.0], responses)
        two = run_synced(args.binary, ("-s", "2"), [0.0, 0.5, 1.0], responses)
        a, b = bpm_values(one), bpm_values(two)
        ensure(one["sync_error"] is None and two["sync_error"] is None,
               f"sample synchronization: {one['sync_error']}, {two['sync_error']}")
        ensure(one["returncode"] == two["returncode"] == 0,
               "sample window exit status")
        ensure(len(a) >= 2 and len(b) >= 2, "sample window BPM missing")
        ensure(all(math.isfinite(value) and value > 0 for value in (*a, *b)),
               f"invalid sample window BPM: {a}, {b}")
        ensure_tempo_matches_beat_bounds(one, a[-1], 1)
        ensure_tempo_matches_beat_bounds(two, b[-1], 2)
        return [one, two]

    def reset_time():
        r = run_synced(args.binary, ("-r", "1"), [0.0, 1.2, 0.5],
                       [(b"one more time", 1), (b"one more time", 2),
                        (b"Tempo:", 1)])
        values = bpm_values(r)
        ensure(r["sync_error"] is None, f"reset synchronization: {r['sync_error']}")
        ensure(r["returncode"] == 0, "reset exit status")
        ensure(len(values) == 1, f"expected one post-reset BPM, got {len(values)}")
        ensure(math.isfinite(values[0]) and values[0] > 0,
               f"invalid post-reset BPM: {values[0]}")
        ensure_tempo_matches_beat_bounds(r, values[0], 1)
        return [r]

    def game_mode():
        r = run(args.binary, ("-g",), [0.0, 0.5])
        ensure(r["returncode"] == 0, "game exit status")
        ensure(any(text in r["stdout"] for text in
                   ("Faster!", "Slower...", "Congratulation")),
               "game feedback missing")
        return [r]

    for name, action in (
        ("version", version), ("help", help_text),
        ("invalid_option", invalid_option), ("q_exit", quit_key),
        ("eof_exit", eof_exit), ("timed_tempo", measured_tempo),
        ("precision_clamp", precision_clamp),
        ("sample_window", sample_window),
        ("reset_time", reset_time), ("game_mode", game_mode),
    ):
        check(name, action)

    summary = {"binary": str(args.binary), "total": len(results),
               "passed": sum(item["passed"] for item in results),
               "failed": sum(not item["passed"] for item in results),
               "cases": results}
    (args.report_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{summary['passed']}/{summary['total']} passed", flush=True)
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
