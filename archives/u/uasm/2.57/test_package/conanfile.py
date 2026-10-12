#!/usr/bin/env python3
"""Conan test_package for UASM 2.57.

Runs test_uasm.sh against the *installed* uasm binary. The harness exercises
the OHOS-portability-sensitive paths (32-bit SHR semantics and CodeGenV2
AVX/VEX encoding) in addition to a plain MASM assembly.
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class UasmTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["uasm"]
        bindir = dep.cpp_info.bindirs[0]
        exe = os.path.join(bindir, "uasm")
        if not os.path.isfile(exe):
            raise ConanException("installed uasm binary not found at %s" % exe)

        here = os.path.dirname(os.path.abspath(__file__))
        script = os.path.join(here, "test_uasm.sh")

        workdir = os.environ.get("TMPDIR") or os.path.join(
            self.build_folder, "uasm-test"
        )
        os.makedirs(workdir, exist_ok=True)

        rc = self.run(
            'sh "%s" "%s" "%s"' % (script, exe, workdir),
            ignore_errors=True,
            env="conanrun",
        )
        if rc != 0:
            raise ConanException("uasm consumer test failed (rc=%s)" % rc)
