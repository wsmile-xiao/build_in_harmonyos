#!/usr/bin/env python3
"""Conan test_package for clzip 1.16.

clzip is a command-line compressor/decompressor for the .lz (lzip) format.
This test verifies:
1. The binary exists and reports its version.
2. Decompression of a fixed upstream .lz file produces output that exactly
   matches the known-good plaintext (byte-for-byte via cmp).
3. stdout decompression (-cd) produces identical output.
4. Integrity test (-t) succeeds on a valid .lz file.
5. Compression roundtrip: clzip compresses real data, then decompresses it
   back byte-for-byte identical.

The compressed fixture is stored as text Base64 (res/test.txt.lz.b64)
because the upstream binary .lz cannot be carried through a PR diff on
GitCode (binary patch data is dropped). It is decoded back to the exact
original bytes here, into a private temp directory (never the source
tree, since Conan's test_package build folder may equal the source
folder), using only the Python standard library. res/test.txt stays as-is.
"""
import base64
import os
import shutil
import tempfile

from conan import ConanFile
from conan.tools.build import can_run


class ClzipTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _restore_fixture(self):
        # Decode the Base64 fixture into a private temp directory so the
        # source tree (and res/) stays text-only and binary-patch-free.
        # The bytes match the upstream clzip-1.16/testsuite/test.txt.lz
        # exactly (verified by SHA256 at recipe authoring time).
        res_dir = os.path.join(self.source_folder, "res")
        b64_path = os.path.join(res_dir, "test.txt.lz.b64")
        work_dir = tempfile.mkdtemp(prefix="clzip_test_")
        lz_path = os.path.join(work_dir, "test.txt.lz")
        with open(b64_path, "rb") as f:
            raw = base64.decodebytes(f.read())
        with open(lz_path, "wb") as f:
            f.write(raw)
        return lz_path, os.path.join(res_dir, "test.txt"), work_dir

    def test(self):
        if can_run(self):
            # VirtualRunEnv adds clzip's bin dir to PATH.
            # Test 1: version check.
            self.run("clzip --version", env="conanrun")
            # Restore the .lz fixture into a temp dir from its text Base64
            # representation, then run the 4 functional checks. The temp dir
            # also holds the roundtrip output files; it is removed afterwards
            # so nothing leaks into the source tree.
            lz_path, txt_path, work_dir = self._restore_fixture()
            try:
                self.run(
                    f'sh "{os.path.join(self.source_folder, "test_clzip.sh")}" '
                    f'"{lz_path}" "{txt_path}" "{work_dir}"',
                    env="conanrun",
                )
            finally:
                shutil.rmtree(work_dir, ignore_errors=True)
