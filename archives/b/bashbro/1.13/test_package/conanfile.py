#!/usr/bin/env python3
"""Conan test_package — bashbro 1.13.

Verifies that the installed bashbro script exists, is syntactically
valid bash, and that the man page is present.

NOTE: CI worker sandbox PATH does not contain `bash` (bash lives in
/data/service/hnp/bin/bash). All bash invocations MUST go through
self.run(..., env="conanrun") which sources conanrun.sh containing
the CI profile's PATH. Never use subprocess.run(["bash", ...]) —
that raises FileNotFoundError on CI.
"""
import os

from conan import ConanFile


class BashbroTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        dep = self.dependencies["bashbro"]
        pkg = dep.package_folder

        # 1. Main script exists at bin/bashbro
        launcher = os.path.join(pkg, "bin", "bashbro")
        assert os.path.isfile(launcher), \
            f"bashbro script not found at {launcher}"

        # 2. R34 实质校验: bash -n 语法检查主脚本
        self.run(f'bash -n "{launcher}"', env="conanrun")

        # 3. Man page exists at share/man/man1/bashbro.1
        man = os.path.join(pkg, "share", "man", "man1", "bashbro.1")
        assert os.path.isfile(man), \
            f"man page not found at {man}"

        # 4. LICENSE exists at share/bashbro/LICENSE
        lic = os.path.join(pkg, "share", "bashbro", "LICENSE")
        assert os.path.isfile(lic), \
            f"LICENSE not found at {lic}"

        # 5. R34 实质校验: 验证脚本内 VERSION 字符串
        #    不执行 bashbro --version：它先做依赖检查（socat/tree/sed），
        #    缺失就 exit 1，无法用于版本验证。
        #    改为 grep 脚本内的 VERSION 声明（declare -r VERSION=1.13）
        self.run(
            f'grep -q "declare -r VERSION=1.13" "{launcher}"',
            env="conanrun",
        )

        # 6. Run the packaged shell test for content verification
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_bashbro.sh")
        self.run(f'bash "{test_script}" "{pkg}"', env="conanrun")
