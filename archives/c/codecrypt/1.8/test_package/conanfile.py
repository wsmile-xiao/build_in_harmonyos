#!/usr/bin/env python3
"""Conan test_package — codecrypt 1.8 (ccr) L1 functional test.

Upstream ships no test suite (see notes.md); test_ccr.sh exercises the
packaged ccr binary end-to-end: version check, full algorithm-suite check
(cryptopp-backed variants included) and a symmetric encrypt/decrypt
round-trip (R34: actually runs the tested package's executable).

ccr is a C++ binary linked against the SDK libc++_shared.so, which is not
part of any conan package; _libcxx_dir() locates it via
clang++ -print-file-name (same approach as the boost1.84 recipes) and adds
it to LD_LIBRARY_PATH alongside the conanrun environment.
"""
import os

from conan import ConanFile


class CodecryptTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _libcxx_dir(self):
        import subprocess as sp
        try:
            located = sp.check_output(
                ["clang++", "-print-file-name=libc++_shared.so"],
                text=True).strip()
            if located and located != "libc++_shared.so" and os.path.isdir(
                    os.path.dirname(located)):
                return os.path.dirname(located)
        except Exception:  # noqa: BLE001
            pass
        return ""

    def test(self):
        ccr = os.path.join(
            self.dependencies["codecrypt"].package_folder, "bin", "ccr")
        if not os.path.isfile(ccr):
            raise RuntimeError(f"ccr not found at {ccr}")

        script = os.path.join(self.source_folder, "test_ccr.sh")
        tmp = os.path.join(self.build_folder, "ccrtest")
        libcxx = self._libcxx_dir()
        extra = f'export LD_LIBRARY_PATH="{libcxx}:$LD_LIBRARY_PATH"; ' \
                if libcxx else ""
        # Test logic lives in test_ccr.sh (L0c test source file); run it
        # under the conanrun env so the packaged binary's shared deps
        # (gmp/fftw) resolve.
        self.run(f'{extra}sh "{script}" "{ccr}" "{tmp}"', env="conanrun")
