#!/usr/bin/env python3
"""Conan test_package for clitest 0.5.0 — shell tool L1 test.

Both scripts drive the packaged tool itself (`sh <pkg>/bin/clitest ...`) with
real test documents, so the assertions exercise clitest's actual parsing,
execution and output-comparison logic rather than a stub.

The interpreter is passed explicitly instead of relying on the shebang: the
packaged script starts with `#!/system/bin/sh` (HarmonyOS path, knowledge
entry E165), which does not exist on a non-HarmonyOS build host. The shebang
itself, and that /system/bin/sh really runs the packaged script, are asserted
in test_clitest_ohos.sh — that assertion reports SKIP when /system/bin/sh is
absent instead of silently passing.

The scripts build their fixtures with printf, never with here-documents: on
the HarmonyOS device /system/bin/sh backs each here-document with a temp file
under the read-only /tmp and silently leaves an empty target file behind (CI
build #56023, knowledge draft E547-draft-3028).
"""

import os

from conan import ConanFile


class ClitestTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["clitest"].package_folder
        clitest_bin = os.path.join(pkg_folder, "bin", "clitest")

        generic = os.path.join(self.recipe_folder, "test_clitest.sh")
        self.run(f'sh "{generic}" "{clitest_bin}"')

        ohos = os.path.join(self.recipe_folder, "test_clitest_ohos.sh")
        self.run(f'sh "{ohos}" "{clitest_bin}"')
