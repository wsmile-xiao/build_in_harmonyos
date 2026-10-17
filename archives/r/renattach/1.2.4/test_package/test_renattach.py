#!/usr/bin/env python3
"""Exercise renattach against a MIME message with a dangerous attachment."""

import os
from pathlib import Path
import shutil
import subprocess
import sys


def require(condition, message):
    if not condition:
        raise AssertionError(message)
    print(f"[ok] {message}")


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: test_renattach.py <renattach-binary>")

    binary = Path(sys.argv[1])
    work_dir = Path.cwd() / "renattach-functional-test"
    try:
        tmp_dir = work_dir / "tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        config = work_dir / "renattach.conf"
        config.write_text(
            "delete_exe = no\n"
            "kill_exe = no\n"
            "use_syslog = no\n"
            "badlist = EXE\n"
            "full_rename = yes\n"
            "new_extension = bad\n",
            encoding="utf-8",
        )

        environment = os.environ.copy()
        environment["TMPDIR"] = str(tmp_dir)

        version = subprocess.run(
            [str(binary), "--version"],
            capture_output=True,
            text=True,
            env=environment,
            check=False,
        )
        require(version.returncode == 0, "--version exits successfully")
        require("renattach 1.2.4" in version.stdout, "version output identifies 1.2.4")

        message = (
            "From: sender@example.com\n"
            "To: receiver@example.com\n"
            "Subject: Test message\n"
            "MIME-Version: 1.0\n"
            "Content-Type: multipart/mixed; boundary=BOUNDARY\n"
            "\n"
            "--BOUNDARY\n"
            "Content-Type: text/plain\n"
            "\n"
            "Message body.\n"
            "--BOUNDARY\n"
            "Content-Type: application/octet-stream; name=\"virus.exe\"\n"
            "Content-Transfer-Encoding: base64\n"
            "Content-Disposition: attachment; filename=\"virus.exe\"\n"
            "\n"
            "SGVsbG8h\n"
            "--BOUNDARY--\n"
        )
        filtered = subprocess.run(
            [str(binary), "--config", str(config)],
            input=message,
            capture_output=True,
            text=True,
            env=environment,
            check=False,
        )
        require(filtered.returncode == 0, "MIME filtering exits successfully")
        output = filtered.stdout.replace("\r\n", "\n")
        require('name="virus_exe.bad"' in output, "Content-Type filename is renamed")
        require(
            'filename="virus_exe.bad"' in output,
            "Content-Disposition filename is renamed",
        )
        require(
            "X-RenAttach-Info: mode=badlist action=rename count=1 (filtered)" in output,
            "filter metadata records one renamed attachment",
        )
        require("Subject: [filtered] Test message" in output, "subject is marked as filtered")
        require("SGVsbG8h" in output, "safe attachment payload is preserved")
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
