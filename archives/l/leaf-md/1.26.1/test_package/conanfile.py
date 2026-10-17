#!/usr/bin/env python3
"""Conan test_package for leaf-md 1.26.1 — consumer view.

Drives the *installed* artefact (the packaged ``leaf`` binary) rather than the
build tree.  Two test groups, both executed by ``leaf_consumer_test.sh``:

  A. 消费者测试 (consumer integration)
     The binary is driven through its public CLI the way an end user would:
     version contract, help contract, Markdown rendering to stdout (file input
     and stdin pipe), and error handling for an unknown option.

  B. 鸿蒙特有测试 (HarmonyOS-specific)
     The packaged ELF is checked against the constraints the HarmonyOS PC
     (aarch64) runtime imposes on executables: AArch64 ELF machine, HarmonyOS
     code signature (``.codesign``) present, and an OHOS-native program
     interpreter / libc dependency instead of glibc.

See test_package/MANIFEST.yml for the upstream test declaration.
"""

import os

from conan import ConanFile
from conan.errors import ConanException


class LeafMdTestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R32: platform guard — never compare against "Linux" alone.
        if str(self.settings.os) not in ("Linux", "OHOS"):
            self.output.info("leaf-md consumer tests are OHOS/Linux-only, skipping")
            return

        dependency = self.dependencies[self.tested_reference_str]
        binary = os.path.join(dependency.package_folder, "bin", "leaf")
        if not os.path.isfile(binary):
            raise ConanException(
                f"packaged leaf binary not found at {binary}"
            )

        # On OHOS /system/bin/sh (mksh) cannot exec ELF binaries, so the test
        # script is launched through bash and receives the artefact path.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        if not os.path.isfile(bash):
            bash = "/bin/bash"
        self.run(
            f'LEAF_BIN="{binary}" "{bash}" leaf_consumer_test.sh',
            env="conanrun",
        )
