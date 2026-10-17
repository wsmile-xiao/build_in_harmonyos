#!/usr/bin/env python3
"""Conan test_package — gtkmm 4.0.0 (Conan L1 官方测试)

消费者视角验证：头文件可包含（gtkmm.h / gdkmm.h），库可链接
（libgtkmm-4.0 / libgdkmm-4.0），二进制可运行（原生 OHOS）。
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
        # 汇总全部依赖（含被测包 gtkmm）的 include 路径：
        # gtkmm 头文件会 include <gtk/gtk.h>/<gdk/gdk.h>（来自 gtk4 组件）
        # 与 <glibmm.h>/<sigc++/sigc++.h>（来自 glibmm/libsigc++ 3.x），
        # 所以必须收集所有依赖的 includedirs 与组件 includedirs。
        incs = []
        libdirs = set()
        for _ref, dep in self.dependencies.items():
            incs += ["-I" + p for p in dep.cpp_info.includedirs]
            for _comp_name, comp in dep.cpp_info.components.items():
                incs += ["-I" + p for p in comp.includedirs]
            if dep.package_folder:
                libdirs.add(os.path.join(dep.package_folder, "lib"))
            for d in dep.cpp_info.libdirs:
                libdirs.add(d)
            for _comp_name, comp in dep.cpp_info.components.items():
                for d in comp.libdirs:
                    libdirs.add(d)
        seen = set()
        uniq = []
        for flag in incs:
            if flag not in seen:
                seen.add(flag)
                uniq.append(flag)
        inc = " ".join(uniq)
        libdir = " ".join("-L" + d for d in sorted(libdirs)) if libdirs else ""

        # R33：编译器从 Conan conf 获取，禁止 ${CXX}。
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cxx = ce.get("cpp") or ce.get("c") or "clang++"

        self.run(
            f"{cxx} test.cpp -o test_probe {inc} "
            f"{libdir} -lgtkmm-4.0 -lglibmm-2.68 -lgiomm-2.68 -lsigc-3.0 -std=c++17"
        )

    def test(self):
        # 交叉 SDK / qemu 常无法运行 OHOS musl 动态链接二进制：只验编译+链接。
        if cross_building(self) or not can_run(self):
            self.output.info("cross-building / cannot run host：只验编译+链接")
            return
        # OHOS: /system/bin/sh (mksh) 不能 exec ELF，用 CONFIG_SHELL bash 包一层
        # （glibmm test_package 同款）。LD_LIBRARY_PATH 显式给出全部依赖 lib 目录。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        ld_path = ":".join(sorted(libdirs)) if "libdirs" in dir() else ""
        if not ld_path:
            ld_path = ":".join(dict.fromkeys(
                l for d in self.dependencies.values()
                for l in list(d.cpp_info.libdirs)
                + [ll for c in d.cpp_info.components.values() for ll in c.libdirs]
            ))
        self.run(f"LD_LIBRARY_PATH={ld_path} {bash} -c './test_probe'")