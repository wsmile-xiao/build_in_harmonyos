#!/usr/bin/env python3
"""Conan test_package for lunzip 1.16.

lunzip is a command-line decompressor for the .lz (lzip) format.
This test verifies:
1. The binary exists and reports its version.
2. Decompression of a fixed .lz file produces output that exactly matches
   the known-good plaintext (byte-for-byte via cmp).
3. stdout decompression (-cd) produces identical output.
4. Integrity test (-t) succeeds on a valid .lz file.

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


class LunzipTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _restore_fixture(self):
        # Decode the Base64 fixture into a private temp directory so the
        # source tree (and res/) stays text-only and binary-patch-free —
        # the regenerated .lz is never written back into the source dir.
        # (Conan's test_package build folder can coincide with the source
        # folder, so build_folder is not a safe place for it either.) The
        # bytes produced match the upstream test.txt.lz exactly (verified
        # at recipe authoring time by SHA256 round-trip).
        res_dir = os.path.join(self.source_folder, "res")
        b64_path = os.path.join(res_dir, "test.txt.lz.b64")
        work_dir = tempfile.mkdtemp(prefix="lunzip_test_")
        lz_path = os.path.join(work_dir, "test.txt.lz")
        with open(b64_path, "rb") as f:
            raw = base64.decodebytes(f.read())
        with open(lz_path, "wb") as f:
            f.write(raw)
        return lz_path, os.path.join(res_dir, "test.txt"), work_dir

    def test(self):
        if can_run(self):
            # VirtualRunEnv adds lunzip's bin dir to PATH.
            # Test 1: version check.
            self.run("lunzip --version", env="conanrun")
            # Restore the .lz fixture into a temp dir from its text Base64
            # representation, then run the 3 functional checks. The temp
            # dir also holds the decompressed output files; it is removed
            # afterwards so nothing leaks into the source tree.
            lz_path, txt_path, work_dir = self._restore_fixture()
            try:
                self.run(
                    f'sh "{os.path.join(self.source_folder, "test_lunzip.sh")}" '
                    f'"{lz_path}" "{txt_path}" "{work_dir}"',
                    env="conanrun",
                )
            finally:
                shutil.rmtree(work_dir, ignore_errors=True)
