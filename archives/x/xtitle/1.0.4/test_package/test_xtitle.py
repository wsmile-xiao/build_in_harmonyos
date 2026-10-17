"""Check the real installed scripts' version and VT escape sequences."""
import os
import pty
import subprocess
import sys


bin_dir = sys.argv[1]
cases = [
    ("xtitle", ["--version"], b"1.0.4\n"),
    ("xtitle", ["-q", "abc"], b"\x1b]2;abc\x07\x1b]1;abc\x07"),
    ("xtitle", ["--quiet", "--title", "abc"], b"\x1b]2;abc\x07"),
    ("xtitle", ["--quiet", "--icon", "abc"], b"\x1b]1;abc\x07"),
    ("xtctl", ["-q", "-f", "red"], b"\x1b]10;red\x07"),
    ("xtctl", ["-q", "-b", "blue"], b"\x1b]11;blue\x07"),
    ("xtctl", ["-q", "-c", "green"], b"\x1b]12;green\x07"),
]
for program, args, expected in cases:
    output = subprocess.check_output([os.path.join(bin_dir, program), *args])
    assert output == expected, (program, args, output, expected)
print(f"xtitle/xtctl package functional assertions: {len(cases)}/{len(cases)} passed")


def ohos_pc_terminal_session():
    """HarmonyOS PC case: no X11, system shell, output delivered to a real PTY.

    The terminal on HarmonyOS PC has no X server, and HMDFS may not honour
    execute bits, so the script is launched as an argument of /system/bin/sh.
    """
    shell = "/system/bin/sh"
    assert os.path.exists(shell), f"HarmonyOS system shell missing: {shell}"
    env = {"PATH": "/system/bin:/bin:/usr/bin", "TERM": "xterm-256color"}
    pid, fd = pty.fork()
    if pid == 0:
        os.execve(shell, [shell, os.path.join(bin_dir, "xtitle"), "HarmonyOS PC"], env)
    output = b""
    while True:
        try:
            chunk = os.read(fd, 4096)
        except OSError:
            break
        if not chunk:
            break
        output += chunk
    _, status = os.waitpid(pid, 0)
    assert os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0, status
    for expected in (b"\x1b]2;HarmonyOS PC\x07", b"title = HarmonyOS PC",
                     b"\x1b]1;HarmonyOS PC\x07", b"icon  = HarmonyOS PC"):
        assert expected in output, (expected, output)


ohos_pc_terminal_session()
print("HarmonyOS PC terminal session (no DISPLAY, /system/bin/sh, PTY): 1/1 passed")
