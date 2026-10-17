#!/usr/bin/env python3
"""Consumer smoke test for packaged rdiff-backup."""

import io
import os
import shutil
import subprocess
import sys
import tempfile

import rdiff_backup.C as c_ext
from rdiff_backup import librsync
import rdiff_backup._librsync as librsync_ext
import yaml


def run_cmd(args, cwd=None):
    result = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "command failed with exit code {}: {}\n{}".format(
                result.returncode, " ".join(args), result.stdout
            )
        )
    return result.stdout


def main():
    assert yaml.safe_load("enabled: true\n") == {"enabled": True}
    assert c_ext.acl_unquote(c_ext.acl_quote(b"hello world")) == b"hello world"
    assert hasattr(librsync_ext, "new_sigmaker")

    basis = io.BytesIO(b"alpha\nbeta\ngamma\n")
    signature = librsync.SigFile(basis).read()
    assert signature

    new_data = b"alpha\nbeta\ngamma\ndelta\n"
    delta = librsync.DeltaFile(signature, io.BytesIO(new_data)).read()
    assert delta

    tmp_root = os.environ.get("RDIFF_BACKUP_TEST_TMP") or os.getcwd()
    with tempfile.TemporaryDirectory(prefix="rdiff-backup-test-", dir=tmp_root) as work:
        basis_path = os.path.join(work, "basis.txt")
        delta_path = os.path.join(work, "delta.bin")
        patched_path = os.path.join(work, "patched.txt")
        with open(basis_path, "wb") as handle:
            handle.write(b"alpha\nbeta\ngamma\n")
        with open(delta_path, "wb") as handle:
            handle.write(delta)
        with open(basis_path, "rb") as basis_handle, open(delta_path, "rb") as delta_handle:
            patched = librsync.PatchedFile(basis_handle, delta_handle).read()
        with open(patched_path, "wb") as handle:
            handle.write(patched)
        assert patched == new_data

        rdiff_backup = shutil.which("rdiff-backup")
        assert rdiff_backup
        version_output = run_cmd([rdiff_backup, "--version"])
        assert "rdiff-backup 2.2.6" in version_output

        src = os.path.join(work, "src")
        dst = os.path.join(work, "dst")
        os.makedirs(src)
        os.makedirs(dst)
        with open(os.path.join(src, "sample.txt"), "w", encoding="utf-8") as handle:
            handle.write("sample payload\n")
        run_cmd([rdiff_backup, "--new", "backup", src, dst], cwd=work)
        assert os.path.isdir(os.path.join(dst, "rdiff-backup-data"))
        assert os.path.isfile(os.path.join(dst, "sample.txt"))

    print("rdiff-backup 2.2.6 ok")


if __name__ == "__main__":
    main()
