#!/usr/bin/env python3
"""Conan test_package — bashish 2.2.4.

Verifies that the installed bashish launcher exists, is syntactically
valid bash, and that the share/bashish/ theme-data tree is present.

NOTE: CI worker sandbox PATH does not contain `bash` (bash lives in
/data/service/hnp/bin/bash). All bash invocations MUST go through
self.run(..., env="conanrun") which sources conanrun.sh containing
the CI profile's PATH. Never use subprocess.run(["bash", ...]) —
that raises FileNotFoundError on CI.
"""
import os

from conan import ConanFile


class BashishTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        dep = self.dependencies["bashish"]
        pkg = dep.package_folder

        # 1. Launcher exists at bin/bashish
        launcher = os.path.join(pkg, "bin", "bashish")
        assert os.path.isfile(launcher), \
            f"bashish launcher not found at {launcher}"

        # 2. R34 实质校验: bash -n 语法检查 launcher
        #    用 env="conanrun" 让 conan 通过 conanrun.sh 找到 bash
        self.run(f'bash -n "{launcher}"', env="conanrun")

        # 3. Theme-data tree exists at share/bashish/
        data = os.path.join(pkg, "share", "bashish")
        assert os.path.isdir(data), \
            f"share/bashish/ theme-data tree not found at {data}"

        # 4. Expected subdirectories present
        for sub in ["main", "themes", "lib", "defaults"]:
            p = os.path.join(data, sub)
            assert os.path.isdir(p), \
                f"expected subdirectory {sub}/ not found at {p}"

        # 5. bash -n syntax check on all installed .sh scripts
        sh_files = []
        for root, _, files in os.walk(data):
            for f in files:
                if f.endswith(".sh"):
                    sh_files.append(os.path.join(root, f))
        assert len(sh_files) >= 1, \
            f"expected 1+ .sh scripts under {data}, got {len(sh_files)}"
        for sh in sh_files:
            self.run(f'bash -n "{sh}"', env="conanrun")

        # 6. Run the packaged shell test for content verification
        #    test_bashish.sh 用 #!/bin/sh + bash 调用，需 conanrun 环境
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_bashish.sh")
        self.run(f'bash "{test_script}" "{pkg}"', env="conanrun")
