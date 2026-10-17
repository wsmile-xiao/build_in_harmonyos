#!/usr/bin/env python3
"""Conan test_package for qsopt 2.5.10.3 — solves a small LP with the exact
rational solver and asserts the exact optimum (42), mirroring the upstream
TAP suite (tests/test_qs.c)."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class QsoptTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # The test uses GMP mpq_t directly (same as upstream test_qs.c).
        self.requires("gmp/6.3.0")

    def test(self):
        # 鸿蒙特有测试：独立于 can_run 执行（检查对象在宿主即可读，不运行
        # OHOS 二进制）。验证本包两个 OHOS 适配点：aarch64-unknown-linux-ohos
        # 三元组产物 ABI（H1）与 4 个 ac_cv_* 探针 pin 生效、无 rpl_* 符号
        # （H2）。计数口径：独立检查项数，共 2 项（MANIFEST/notes 一致）。
        if str(self.settings.os) == "OHOS":
            lib = os.path.join(self.dependencies["qsopt"].package_folder, "lib", "libqsopt_ex.a")
            check = os.path.join(os.path.dirname(__file__), "ohos_platform_check.sh")
            self.run(f"sh {check} {lib}")
        if not can_run(self):
            # Cross build (OHOS binary cannot execute on the build machine):
            # the recipe's own `make check` is skipped the same way. CI builds
            # natively on OHOS where can_run=True and this full test runs.
            self.output.info("Skipping consumer test: cross-build (can_run=False)")
            return
        qsopt = self.dependencies["qsopt"]
        gmp = self.dependencies["gmp"]
        # Static libqsopt_ex.a references gz*/BZ2* symbols from zlib/bzip2
        # (eg_io.c), so consumers must link those too (transitive requires).
        zlib = self.dependencies["zlib"]
        bzip2 = self.dependencies["bzip2"]
        inc = " ".join(f"-I{os.path.join(d.package_folder, p)}"
                       for d in (qsopt, gmp) for p in d.cpp_info.includedirs)
        lib = " ".join(f"-L{os.path.join(d.package_folder, p)}"
                       for d in (qsopt, gmp, zlib, bzip2) for p in d.cpp_info.libdirs)
        link = " ".join(f"-l{l}" for d in (qsopt, gmp, zlib, bzip2) for l in d.cpp_info.libs)
        syslibs = " ".join(f"-l{l}" for l in qsopt.cpp_info.system_libs)
        self.run(
            f"clang test.c -o test {inc} {lib} {link} {syslibs}",
            env="conanbuild",
        )
        self.run("./test", env="conanrun")
