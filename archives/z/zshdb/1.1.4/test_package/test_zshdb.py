import os
import subprocess
import sys

binary, source = sys.argv[1:]
version = subprocess.run(
    [binary, "--version"], text=True, capture_output=True, timeout=15, check=True
)
assert "zshdb, release 1.1.4" in version.stdout, version.stdout + version.stderr

env = os.environ.copy()
env["TMPDIR"] = os.getcwd()
debug = subprocess.run(
    [
        binary, "-q", "--no-init", "--no-highlight",
        "-x", os.path.join(source, "commands.txt"),
        os.path.join(source, "sample.zsh"),
    ],
    text=True, capture_output=True, timeout=20, env=env
)
assert debug.returncode in (0, 128), f"exit={debug.returncode}\n{debug.stdout}\n{debug.stderr}"
assert "ZSHDB_SAMPLE_RAN" in debug.stdout, debug.stdout + debug.stderr
assert "Debugged program terminated normally." in debug.stdout, debug.stdout + debug.stderr
print("zshdb installed-package version and noninteractive debugging: PASS")
