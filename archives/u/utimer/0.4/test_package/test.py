import os
import subprocess
import sys
import tempfile
import time


binary = sys.argv[1]
environment = dict(os.environ, LC_ALL="C", LANG="C")


def run(args, expected=0, timed=False):
    start = time.monotonic()
    # Genuine noninteractive finite timing: EOF must stop only the key watcher,
    # not short-circuit the timer. communicate drains output during execution.
    process = subprocess.run([binary, *args], input=b"", stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, env=environment, timeout=8)
    output = process.stdout.decode("utf-8", "replace")
    assert process.returncode == expected, (args, process.returncode, output)
    if timed:
        assert 0.08 <= time.monotonic() - start < 5, output
    return output


assert "utimer 0.4" in run(["--version"])
print("ok - installed version", flush=True)
assert "countdown" in run(["--help"])
print("ok - installed help", flush=True)
assert "Elapsed Time" in run(["-t", "200ms"], timed=True)
print("ok - finite timer", flush=True)
assert "Time Remaining" in run(["-c", "200ms"], timed=True)
print("ok - finite countdown", flush=True)
with tempfile.TemporaryFile() as output:
    start = time.monotonic()
    process = subprocess.Popen([binary, "-t", "200ms"], stdin=subprocess.PIPE,
                               stdout=output, stderr=subprocess.STDOUT, env=environment)
    try:
        # No EOF, quit key or signal: timer must finish with stdin still open.
        process.wait(timeout=8)
        assert process.returncode == 0
        assert 0.08 <= time.monotonic() - start < 5
        output.seek(0)
        assert b"Elapsed Time" in output.read()
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
        output.seek(0)
        print(output.read().decode("utf-8", "replace"), flush=True)
        raise
    finally:
        process.stdin.close()
print("ok - timer exits with stdin open", flush=True)
assert "limits" in run(["--limits"]).lower()
print("ok - limits", flush=True)
assert "No option" in run([], expected=1)
print("ok - missing option rejected", flush=True)
assert "Unknown option" in run(["--not-a-real-option"], expected=1)
print("ok - unknown option rejected", flush=True)
print("UTIMER_CONSUMER_RESULT=8/8", flush=True)
