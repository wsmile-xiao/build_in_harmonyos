#!/usr/bin/env python3
"""Exercise the packaged zbackup CLI with a real backup/restore cycle."""

import argparse
import hashlib
import os
import platform
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path


def run_checked(argv, env, input_data=None):
    result = subprocess.run(
        argv,
        input=input_data,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        timeout=180,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "%s failed with exit code %d\nstdout: %s\nstderr: %s"
            % (
                " ".join(argv),
                result.returncode,
                result.stdout.decode(errors="replace")[-1500:],
                result.stderr.decode(errors="replace")[-3000:],
            )
        )
    return result


def exercise(executable, harmonyos):
    if harmonyos and os.name != "posix":
        raise RuntimeError("the HarmonyOS runtime case must execute on a POSIX HarmonyOS host")

    # zbackup 1.5 exposes help through -O help, not --help or --version.
    run_checked([executable, "-O", "help"], os.environ.copy())

    temp_parent = (
        os.environ.get("OHC_TEST_TMPDIR")
        or os.environ.get("TMPDIR")
        or tempfile.gettempdir()
    )
    os.makedirs(temp_parent, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="zbackup-test-", dir=temp_parent) as work:
        work = Path(work)
        repo = work / "repo"
        scratch = work / "harmony-tmp" if harmonyos else work / "tmp"
        scratch.mkdir()
        # Keep the caller-provided TMPDIR alive while zbackup cleans up its own files.
        sentinel = scratch / "preserve-tmpdir"
        sentinel.write_text("test-owned temporary directory\n", encoding="utf-8")

        env = os.environ.copy()
        env["TMPDIR"] = str(scratch)
        run_checked(
            [executable, "--non-encrypted", "-O", "paths.respect_tmp", "init", str(repo)],
            env,
        )

        backups = repo / "backups"
        backups.mkdir(exist_ok=True)
        poisoned_repo_tmp = repo / "tmp"
        if harmonyos:
            # The OHOS-specific regression: make zbackup's default repository
            # temp path unusable. Backup/restore must honor paths.respect_tmp
            # and write temporary files through the HarmonyOS-provided TMPDIR.
            if poisoned_repo_tmp.is_dir():
                shutil.rmtree(poisoned_repo_tmp)
            elif poisoned_repo_tmp.exists():
                poisoned_repo_tmp.unlink()
            poisoned_repo_tmp.write_text("must not be used as a directory\n", encoding="utf-8")

        payload = (b"zbackup HarmonyOS round-trip\n" + bytes(range(256))) * 4096
        backup = backups / "conan-test-backup"
        run_checked(
            [
                executable,
                "--non-encrypted",
                "-O",
                "paths.respect_tmp",
                "-O",
                "threads=1",
                "backup",
                str(backup),
            ],
            env,
            input_data=payload,
        )
        if not backup.is_file() or backup.stat().st_size == 0:
            raise RuntimeError("zbackup did not create a non-empty backup file")

        restored = run_checked(
            [
                executable,
                "--non-encrypted",
                "-O",
                "paths.respect_tmp",
                "restore",
                str(backup),
            ],
            env,
        ).stdout
        if hashlib.sha256(restored).digest() != hashlib.sha256(payload).digest():
            raise RuntimeError("restored data does not match the original input")

        # Exercise OpenSSL-backed repository encryption as well as the
        # non-encrypted path used by the HarmonyOS temp-directory check.
        encrypted_repo = work / "encrypted-repo"
        encrypted_backups = encrypted_repo / "backups"
        password_file = work / "password.txt"
        password_file.write_text("zbackup-test-password\n", encoding="utf-8")
        if os.name == "posix":
            password_file.chmod(0o600)
        run_checked(
            [
                executable,
                "--password-file",
                str(password_file),
                "-O",
                "paths.respect_tmp",
                "init",
                str(encrypted_repo),
            ],
            env,
        )
        encrypted_backups.mkdir(exist_ok=True)
        encrypted_backup = encrypted_backups / "conan-test-encrypted-backup"
        run_checked(
            [
                executable,
                "--password-file",
                str(password_file),
                "-O",
                "paths.respect_tmp",
                "-O",
                "threads=1",
                "backup",
                str(encrypted_backup),
            ],
            env,
            input_data=payload,
        )
        if not encrypted_backup.is_file() or encrypted_backup.stat().st_size == 0:
            raise RuntimeError("zbackup did not create an encrypted backup file")
        encrypted_restored = run_checked(
            [
                executable,
                "--password-file",
                str(password_file),
                "-O",
                "paths.respect_tmp",
                "restore",
                str(encrypted_backup),
            ],
            env,
        ).stdout
        if hashlib.sha256(encrypted_restored).digest() != hashlib.sha256(payload).digest():
            raise RuntimeError("encrypted restore does not match the original input")

        if harmonyos:
            if not poisoned_repo_tmp.is_file():
                raise RuntimeError("zbackup changed the deliberately unusable repo/tmp path")
            leftovers = [path.name for path in scratch.iterdir() if path != sentinel]
            if leftovers:
                raise RuntimeError("zbackup left temporary files in TMPDIR: %s" % leftovers)
            print("HarmonyOS TMPDIR override: PASS (%s)" % platform.platform())

        print("zbackup plain and encrypted backup/restore: PASS (%d bytes each)" % len(payload))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("executable")
    parser.add_argument("--harmonyos", action="store_true")
    args = parser.parse_args()
    exercise(args.executable, args.harmonyos)


if __name__ == "__main__":
    main()
