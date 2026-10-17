#!/usr/bin/env python3
"""Conan test_package — pangomm-2.46 2.46.5 (Conan L1 官方测试)

消费者视角验证：头文件可包含（pangomm.h / pangommconfig.h），库可链接
（libpangomm-1.4），二进制可运行（原生 OHOS）。
编译命令从 Conan conf 取编译器（R33），不裸用 shell 环境变量。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run, cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # 汇总全部依赖（含被测包 pangomm）的 include 路径：
        # pangomm 头文件会 include <pango/pango.h>（来自 pango）、
        # <glibmm.h>/<cairomm/...>（来自 glibmm/cairomm）与 <sigc++/sigc++.h>，
        # 所以必须收集所有依赖的 includedirs。
        incs = []
        for _ref, dep in self.dependencies.items():
            incs += ["-I" + p for p in dep.cpp_info.includedirs]
            for _comp_name, comp in dep.cpp_info.components.items():
                incs += ["-I" + p for p in comp.includedirs]
        seen = set()
        uniq = []
        for flag in incs:
            if flag not in seen:
                seen.add(flag)
                uniq.append(flag)
        inc = " ".join(uniq)

        # 所有依赖包的 package_folder/lib 并集（含被测包 pangomm）。
        libdirs = set()
        for d in self.dependencies.values():
            if d.package_folder:
                libdirs.add(os.path.join(d.package_folder, "lib"))
        libdir = " ".join("-L" + d for d in libdirs) if libdirs else ""

        # R33：编译器从 Conan conf 获取，禁止 ${CXX}。
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cxx = ce.get("cpp") or ce.get("c") or "clang++"

        # pangomm 2.46.x 为旧 ABI：-lpangomm-1.4 -lcairomm-1.0 -lglibmm-2.4
        # -lsigc-2.0；本包无 giomm 依赖（pangomm 2.46 无 gio 绑定）。
        self.run(
            f"{cxx} test.cpp -o test_probe {inc} "
            f"{libdir} -lpangomm-1.4 -lcairomm-1.0 -lglibmm-2.4 "
            f"-lsigc-2.0 -std=c++17"
        )

    def test(self):
        # 交叉 SDK / qemu 常无法运行 OHOS musl 动态链接二进制：只验编译+链接。
        if cross_building(self) or not can_run(self):
            self.output.info("cross-building / cannot run host：只验编译+链接")
            return
        # OHOS: /system/bin/sh (mksh) 不能 exec ELF，用 CONFIG_SHELL bash 包一层
        # （libsigc/glibmm test_package 同款）。LD_LIBRARY_PATH 显式给出全部依赖 lib 目录。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        libs = []
        for _ref, d in self.dependencies.items():
            libs += list(d.cpp_info.libdirs)
            for _comp_name, comp in d.cpp_info.components.items():
                libs += list(comp.libdirs)
        # OHOS shared libs 需要 libc++_shared.so（SDK 提供，不是 Conan 包）。
        _sdk_libcxx = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos"
        if os.path.isdir(_sdk_libcxx):
            libs.append(_sdk_libcxx)
        ld_path = ":".join(dict.fromkeys(l for l in libs if l))
        self.run(f"LD_LIBRARY_PATH={ld_path} {bash} -c './test_probe'")
