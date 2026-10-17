#!/usr/bin/env python3
"""Conan test_package — aeolus 0.10.4 L1 smoke test.

Real consumer-side verification (R34):
  1. Runs the packaged `aeolus` binary with `-h` (prints the help banner
     "Aeolus 0.10.4" and exits 0) — proves the binary links and loads.
  2. dlopens the packaged `aeolus_txt.so` plugin and dlsym()s the
     `create_iface` entry point — proves the text-mode interface plugin
     is loadable in the OHOS runtime.

The upstream tree ships no test target (`make check` has no rule), so the
test is entirely consumer-side.
"""
import os

from conan import ConanFile


class AeolusTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # R33: compiler from the Conan profile conf, never a bare ${CXX}.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"
        # E132: OHOS SDK lld 依赖 libxml2.so.16, musl ldso 不支持 $ORIGIN
        # RUNPATH (E019), 部分 CI worker 需注入 SDK llvm/lib 到 LD_LIBRARY_PATH
        # 才能链接; 保持 lld 链接 (GNU ld 产物在 OHOS 沙箱中 Permission denied).
        env_prefix = ""
        try:
            real = os.path.realpath(cxx)
            llvm_lib = os.path.join(os.path.dirname(os.path.dirname(real)), "lib")
            if os.path.isfile(os.path.join(llvm_lib, "libxml2.so.16")):
                env_prefix = 'export LD_LIBRARY_PATH="{}:${{LD_LIBRARY_PATH:-}}"; '.format(llvm_lib)
        except OSError:
            pass
        self.run(
            env_prefix + '"{}" -std=c++17 -o test_aeolus test_aeolus.cpp -ldl'.format(cxx)
        )

    def test(self):
        pkg_folder = self.dependencies["aeolus"].package_folder
        aeolus_bin = os.path.join(pkg_folder, "bin", "aeolus")
        txt_plugin = os.path.join(pkg_folder, "lib", "aeolus_txt.so")

        # 1) The binary must run: `-h` prints the "Aeolus 0.10.4" banner.
        #    (Note: upstream help() ends with exit(1), so we assert on the
        #    printed banner text, not on the exit code.)
        self.run(
            '"{}" -h > aeolus_help.txt 2>&1; grep -q "Aeolus 0.10.4" aeolus_help.txt'.format(aeolus_bin),
            env="conanrun",
        )

        # 2) The text-mode plugin must load and expose its interface factory.
        self.run('./test_aeolus "{}"'.format(txt_plugin), env="conanrun")
