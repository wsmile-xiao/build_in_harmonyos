"""Boot the installed YAZE-AG binary and leave via its monitor command."""

import os
import subprocess
import sys


binary = sys.argv[1]
res = os.path.abspath(os.path.join(os.path.dirname(binary), "..", "res"))
boot_utils = os.path.join(res, "disks", "BOOT_UTILS.ydsk")
cpm_sys = os.path.join(res, "disks", "CPM3_SYS.ydsk")
result = subprocess.run(
    [binary, "-s", "/dev/null", f"mount a {boot_utils}",
     f"mount b {cpm_sys}", "mount", "quit"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    timeout=15,
    check=False,
)
assert result.returncode == 0, result.stdout
assert "final release 2.51.3" in result.stdout, result.stdout
assert "Running '" in result.stdout and "yaze-cpm3.boot" in result.stdout, result.stdout
assert "A: r/" in result.stdout and "BOOT_UTILS.ydsk" in result.stdout, result.stdout
assert "B: r/" in result.stdout and "CPM3_SYS.ydsk" in result.stdout, result.stdout
print("YAZE-AG boot, disk mounts and monitor exit: PASS")
