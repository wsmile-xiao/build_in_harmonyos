#!/usr/bin/env python3
import subprocess
import sys

executable = sys.argv[1]
result = subprocess.run(
    [executable, "-v"],
    check=False,
    capture_output=True,
    text=True,
)

output = result.stdout + result.stderr
assert result.returncode == 0, result
assert "abduco-0.6" in output, output

print("abduco API/CLI smoke test: version assertion passed")
