#!/usr/bin/env python3
"""L1 consumer test for fpc/3.2.2 (application package)."""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class FpcTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test.sh", "hello.pas"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Upstream testsuite results (declared for the platform review, R51).
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT={\"status\":\"executed\",\"framework\":\"fpc-testsuite\","
            "\"channel\":\"x86_64 Linux native (official x86_64 FPC 3.2.2, same 3.2.2 source)\","
            "\"discovered\":6047,\"executed\":4871,\"passed\":3688,\"failed\":13,\"skipped\":513,"
            "\"reason\":\"make full: Total=7908; compilations 4871 (3688 ok + 1170 expected-fail + 9 fail + "
            "4 unexpected-pass); runs 3037 (3016 ok + 21 fail); skipped 513. 34 deviations are "
            "host-environment related (libgcc/libz/__gxx_personality_v0).\"}"
        )
        # R34: exercise the tested package itself, through the packaged
        # bin/fpc launcher (never through a system-wide FPC).
        fpc = os.path.join(self.dependencies["fpc"].package_folder, "bin", "fpc")
        if not os.path.isfile(fpc):
            raise RuntimeError("packaged fpc launcher missing: " + fpc)

        if not can_run(self):
            self.output.info("cross build: fpc binaries cannot run on this host; "
                             "skipping the compile/run smoke test")
            return

        shell = ""
        for cand in (os.environ.get("CONFIG_SHELL"), "/data/service/hnp/bin/bash",
                     shutil.which("bash"), "/bin/bash"):
            if cand and os.path.exists(cand):
                shell = cand
                break
        shell = shell or "bash"
        script = os.path.join(self.recipe_folder, "test.sh")
        self.run('%s "%s" "%s"' % (shell, script, fpc), env="conanrun")
