#!/usr/bin/env python3
"""Conan test_package — planetblupi 1.15.1（HarmonyOS PC 消费者验证）。

执行两段真实消费验证：
  1. 结构断言（check_planetblupi.py）——ELF 架构、产物存在、资源目录
  2. rule12 端到端消费者用例（test_planetblupi_e2e.c）——dlopen 产物 +
     fork/exec 真实运行 --help + resources 资源消费路径
"""
import os
import subprocess
import sys

from conan import ConanFile
from conan.tools.env import Environment


class PlanetblupiTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        bin_path = os.path.join(pkg, "bin", "planetblupi")
        res_dir = os.path.join(pkg, "share", "planetblupi", "resources")
        assert os.path.isfile(bin_path), f"planetblupi not found at {bin_path}"
        self.output.info(f"planetblupi found: {bin_path}")

        env = Environment()
        env.define("PLANETBLUPI_BIN", bin_path)
        env.define("PLANETBLUPI_RES_DIR", res_dir)
        with env.vars(self).apply():
            checker = os.path.join(self.source_folder, "check_planetblupi.py")
            self.run(f'"{sys.executable}" "{checker}"')

            # rule12 端到端消费者用例（编译器来自 profile conf 绝对路径，
            # 回退本机 clang；CC 裸名问题 kamailio-unixodbc #61596 已验证）
            compilers = self.conf.get("tools.build:compiler_executables",
                                      default={}, check_type=dict)
            cc = compilers.get("c") or "clang"
            if not os.path.isabs(cc) or not os.path.isfile(cc):
                sdk_cc = ("/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18"
                          "/ohos/native/llvm/bin/aarch64-unknown-linux-ohos-clang")
                if os.path.isfile(sdk_cc):
                    cc = sdk_cc
            e2e_src = os.path.join(self.source_folder, "test_planetblupi_e2e.c")
            e2e_bin = os.path.join(self.build_folder, "test_planetblupi_e2e")
            subprocess.run([cc, "-std=c11", e2e_src, "-o", e2e_bin, "-ldl"],
                           check=True)
            # e2e 真实运行需要 dlopen 解析 planetblupi 的全部动态依赖
            # （ffmpeg/SDL2 系 .so）——收集各依赖包 lib 目录注入 LD_LIBRARY_PATH
            lib_dirs = []
            for dep in self.dependencies.values():
                for d in dep.cpp_info.libdirs:
                    if os.path.isdir(d):
                        lib_dirs.append(d)
            run_env = Environment()
            run_env.define("PLANETBLUPI_BIN", bin_path)
            run_env.define("PLANETBLUPI_RES_DIR", res_dir)
            if lib_dirs:
                run_env.define("LD_LIBRARY_PATH", os.pathsep.join(lib_dirs))
            with run_env.vars(self).apply():
                self.run(f'"{e2e_bin}" "{bin_path}" "{res_dir}"')
