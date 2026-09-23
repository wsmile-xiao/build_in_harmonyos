#!/usr/bin/env python3
"""Functional test for pipes-sh package installation."""
import os
import shutil
import subprocess
import sys


def main():
    pkg_dir = sys.argv[1]
    script_path = os.path.join(pkg_dir, "bin", "pipes.sh")

    assert os.path.isfile(script_path), f"pipes.sh not found at {script_path}"
    assert os.access(script_path, os.X_OK), f"pipes.sh is not executable: {script_path}"

    with open(script_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    assert "1.3.0" in content, "Version string '1.3.0' not found in pipes.sh"
    assert "#!/usr/bin/env bash" in content, "Bash shebang not found in pipes.sh"

    bash_path = shutil.which("bash")
    assert bash_path is not None, "bash executable not found in PATH"
    missing_commands = [
        command for command in ("tput", "stty", "reset")
        if shutil.which(command) is None
    ]
    if missing_commands:
        print("warning: optional terminal commands not found in PATH: "
              + ", ".join(missing_commands))

    r = subprocess.run([bash_path, "-n", script_path],
                       capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, f"bash -n syntax check failed: {r.stderr}"

    if os.name == "nt":
        version = subprocess.run([bash_path, script_path, "-v"],
                                 capture_output=True, text=True, timeout=30)
    else:
        version = subprocess.run([script_path, "-v"],
                                 capture_output=True, text=True, timeout=30)
    assert version.returncode == 0, f"version check failed: {version.stderr}"
    assert "1.3.0" in version.stdout, "Version output does not contain 1.3.0"

    man_path = os.path.join(pkg_dir, "share", "man", "man6", "pipes.sh.6")
    assert os.path.isfile(man_path), f"Man page not found at {man_path}"

    license_dir = os.path.join(pkg_dir, "licenses")
    assert os.path.isdir(license_dir), f"Licenses directory not found at {license_dir}"

    print("pipes-sh 1.3.0: all tests passed")


if __name__ == "__main__":
    main()
