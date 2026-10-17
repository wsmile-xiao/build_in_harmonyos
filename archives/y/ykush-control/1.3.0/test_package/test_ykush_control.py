import json
import subprocess
import sys


def run_capture(*command):
    completed = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=15,
        check=False,
    )
    print("[cmd]", " ".join(command))
    print(completed.stdout)
    return completed.returncode, completed.stdout


def assert_contains(output, needle, label):
    if needle not in output:
        raise AssertionError(f"{label}: missing {needle!r}\n{output}")
    print(f"PASS: {label}")


def main():
    ykushcmd = sys.argv[1] if len(sys.argv) > 1 else "ykushcmd"

    rc, help_output = run_capture(ykushcmd, "--help")
    assert_contains(help_output, "YKUSHCMD Version 1.3.0", "help reports program version")
    assert_contains(help_output, "Usage:", "help reports usage")

    rc, board_help = run_capture(ykushcmd, "-h")
    assert_contains(board_help, "YKUSH board options", "board help reports YKUSH options")
    assert_contains(
        board_help,
        "Power Down/Off downstream port",
        "board help reports port power command",
    )

    rc, list_output = run_capture(ykushcmd, "-l")
    if rc != 0:
        raise AssertionError(f"board listing exited {rc}\n{list_output}")
    assert_contains(list_output, "Attached YKUSH Boards", "list command reports board section")

    rc, invalid_output = run_capture(ykushcmd, "bogus-command")
    if rc == 0:
        raise AssertionError(f"invalid command unexpectedly succeeded\n{invalid_output}")
    assert_contains(invalid_output, "Usage:", "invalid command prints usage")

    print(
        "HMBS_TEST_PACKAGE_RESULT="
        + json.dumps(
            {
                "executed": True,
                "passed": True,
                "cases": 4,
                "assertions": 7,
                "command": "python test_ykush_control.py <ykushcmd>",
            },
            separators=(",", ":"),
        )
    )


if __name__ == "__main__":
    main()
