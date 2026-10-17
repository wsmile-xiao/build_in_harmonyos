#!/usr/bin/env python3
"""Consumer test for the packaged rt-app executable (Conan L1).

Runs the *installed* rt-app binary through its real command-line contract and
asserts on the artefacts it writes, so the test depends on the real package
(R34) instead of rebuilding the sources. Includes HarmonyOS-specific cases for
the scheduling surface the adaptation rewired (see ohos_sched_test.c).
"""
import os

from conan import ConanFile


class RtAppTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        rt_app = os.path.join(self.dependencies[self.tested_reference_str].package_folder,
                              "bin", "rt-app")
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "run_tests.sh")
        src_dir = os.path.dirname(os.path.abspath(__file__))
        work_dir = os.path.join(self.build_folder, "run-tests")

        # The same cross compiler that built the package also compiles the
        # HarmonyOS verification program, so it targets the same ABI.
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        cc = compilers.get("c", "cc") if isinstance(compilers, dict) else "cc"

        self.run(f'sh "{script}" "{rt_app}" "{cc}" "{work_dir}" "{src_dir}"',
                 env="conanrun")