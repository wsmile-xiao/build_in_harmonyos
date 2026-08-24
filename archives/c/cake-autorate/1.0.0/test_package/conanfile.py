#!/usr/bin/env python3
"""Conan test_package — cake-autorate 1.0.0.

Verifies that the installed cake-autorate scripts exist, are
syntactically valid bash, and that the license file is present.

Pure shell script package — tests use bash -n via conanrun env.
"""
import os

from conan import ConanFile


class CakeAutorateTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        dep = self.dependencies["cake-autorate"]
        pkg = dep.package_folder

        # 1. Main script exists at bin/cake-autorate.sh
        launcher = os.path.join(pkg, "bin", "cake-autorate.sh")
        assert os.path.isfile(launcher), \
            f"cake-autorate.sh not found at {launcher}"

        # 2. R34 实质校验: bash -n 语法检查主脚本
        self.run(f'bash -n "{launcher}"', env="conanrun")

        # 3. Verify all 4 installed scripts exist
        expected_scripts = [
            "cake-autorate.sh",
            "cake-autorate-setup.sh",
            "cake-autorate-config.sh",
            "cake-autorate",
        ]
        for s in expected_scripts:
            p = os.path.join(pkg, "bin", s)
            assert os.path.isfile(p), \
                f"expected script {s} not found at {p}"

        # 4. bash -n syntax check on all bash scripts
        for s in expected_scripts:
            p = os.path.join(pkg, "bin", s)
            self.run(f'bash -n "{p}"', env="conanrun")

        # 5. LICENCE.md license file exists
        lic = os.path.join(pkg, "share", "cake-autorate", "LICENCE.md")
        assert os.path.isfile(lic), \
            f"LICENCE.md not found at {lic}"

        # 6. Run the packaged shell test for content verification
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_cake_autorate.sh")
        self.run(f'bash "{test_script}" "{pkg}"', env="conanrun")
