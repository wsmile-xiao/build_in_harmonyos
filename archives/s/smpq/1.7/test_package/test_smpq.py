#!/usr/bin/env python3
"""Exercise the packaged smpq binary from a consumer's point of view.

Usage: test_smpq.py <path-to-smpq>

smpq is a command line utility, so this script drives the packaged binary end
to end on a real MPQ archive created by the tool itself:

1. ``smpq --version`` reports the release;
2. create an archive from a source file, then list and inspect it;
3. extract that entry into a different directory and byte-compare with the
   original — proving the StormLib link, the MPQ write path and the read path
   all work from a consumer's point of view.

Note on paths: MPQ stores the *hash* of the name handed to the tool, so the
archive is created from src_dir with a bare relative name.  Passing an
absolute path would both bloat the listfile with the build-machine prefix and
make extraction recreate that absolute path (ending in a spurious "File
exists").

Everything happens in a temp dir on the local filesystem: no network, no
display, no external assets.
"""
import os
import shutil
import subprocess
import sys
import tempfile


def main():
    smpq = sys.argv[1]
    assert os.path.isfile(smpq), smpq

    tmpdir = tempfile.mkdtemp(prefix="smpq-test-")
    try:
        src_dir = os.path.join(tmpdir, "src")
        out_dir = os.path.join(tmpdir, "out")
        os.makedirs(src_dir)
        os.makedirs(out_dir)

        payload = b"smpq MPQ round-trip payload for HarmonyOS\n" * 4
        with open(os.path.join(src_dir, "payload.txt"), "wb") as fh:
            fh.write(payload)

        archive = os.path.join(tmpdir, "consumer.mpq")

        def run(args, cwd=tmpdir):
            result = subprocess.run([smpq] + list(args), cwd=cwd,
                                    capture_output=True, text=True, timeout=300)
            assert result.returncode == 0, (
                "smpq %s failed: %s" % (" ".join(args),
                                        (result.stdout or "") + (result.stderr or "")))
            return result

        # 1) Version banner (also exercises StormLib's copyright path).
        run(["--version"])

        # 2) Create the archive from a bare relative name, then inspect it.
        run(["--create", archive, "payload.txt"], cwd=src_dir)
        assert os.path.isfile(archive), "archive was not created"
        assert os.path.getsize(archive) > 0, "archive is empty"

        run(["--info", archive])
        run(["--list", archive])

        # 3) Extract (relative to the current directory) and byte-compare.
        run(["--extract", archive], cwd=out_dir)
        extracted = os.path.join(out_dir, "payload.txt")
        assert os.path.isfile(extracted), "payload.txt not extracted"
        with open(extracted, "rb") as fh:
            got = fh.read()
        assert got == payload, "extracted payload differs from the original"
        print("smpq archive create/info/list/extract round trip OK")
        print("SMPQ-CONSUMER-OK")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


main()
