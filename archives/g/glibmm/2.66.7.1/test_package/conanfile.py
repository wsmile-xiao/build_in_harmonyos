#!/usr/bin/env python3
"""Conan test_package — glibmm 2.66.7 (Conan L1 官方测试)

消费者视角验证：头文件可包含（glibmm.h / giomm.h / sigc++），库可链接
（libglibmm-2.4 / libgiomm-2.4），二进制可运行（原生 OHOS）。
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
        # 汇总全部依赖（含被测包 glibmm）的 include 路径：
        # glibmm 头文件会 include <glib.h>/<glib-object.h>（来自 glib 组件）
        # 与 <sigc++/sigc++.h>（来自 libsigc++），所以必须收集所有依赖的 includedirs。
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

        # glibmm 包自身的 libdir（组件与顶层取并集），加上依赖 libsigc 的 libdir。
        dep = self.dependencies["glibmm"]
        libdirs = set()
        # 直接以每个依赖包的 package_folder/lib 为准（cpp_info.libdirs 偶发带 -L 前缀）。
        for d in self.dependencies.values():
            if d.package_folder:
                libdirs.add(os.path.join(d.package_folder, "lib"))
        libdir = " ".join("-L" + d for d in libdirs) if libdirs else "-L" + os.path.join(dep.package_folder, "lib")

        # R33：编译器从 Conan conf 获取，禁止 ${CXX}。
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cxx = ce.get("cpp") or ce.get("c") or "clang++"

        # libdir 已含 "-L" 前缀（libdirs 每个条目 join 时加 -L），不能再次补 -L，
        # 否则生成 "-L-L/... " 畸形标志导致 -lsigc-2.0 找不到。
        self.run(
            f"{cxx} test.cpp -o test_probe {inc} "
            f"{libdir} -lglibmm-2.4 -lgiomm-2.4 -lsigc-2.0 -std=c++17"
        )

    def test(self):
        # 交叉 SDK / qemu 常无法运行 OHOS musl 动态链接二进制：只验编译+链接。
        if cross_building(self) or not can_run(self):
            self.output.info("cross-building / cannot run host：只验编译+链接")
            return
        # OHOS: /system/bin/sh (mksh) 不能 exec ELF，用 CONFIG_SHELL bash 包一层
        # （libsigc test_package 同款）。LD_LIBRARY_PATH 显式给出全部依赖 lib 目录，
        # 保证 libglibmm/libgiomm/libglib/libgio/libsigc 运行时可见。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        libs = []
        for _ref, d in self.dependencies.items():
            libs += list(d.cpp_info.libdirs)
            for _comp_name, comp in d.cpp_info.components.items():
                libs += list(comp.libdirs)
        ld_path = ":".join(dict.fromkeys(l for l in libs if l))
        self.run(f"LD_LIBRARY_PATH={ld_path} {bash} -c './test_probe'")
