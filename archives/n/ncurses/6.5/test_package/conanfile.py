#!/usr/bin/env python3
"""test_package — 验证 ncurses 宽字符静态库可编译链接并运行."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class NCursesTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # R33：不裸用 shell 环境变量；通过 Conan conf
            # tools.build:compiler_executables 获取 C 编译器完整路径
            # （CI/Conan 环境已设置），未设置时回退 settings.compiler 名称。
            cc_map = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
            cc = cc_map.get("c") or str(self.settings.compiler)
            src = os.path.join(self.source_folder, "src", "test_ncurses.c")
            bin_path = os.path.join(self.build_folder, "test_ncurses")
            pkg = self.dependencies["ncurses"]
            inc_flags = " ".join(
                f"-I{os.path.join(pkg.package_folder, d)}" for d in pkg.cpp_info.includedirs
            )
            lib_flags = " ".join(
                f"-L{os.path.join(pkg.package_folder, d)}" for d in pkg.cpp_info.libdirs
            )
            # 宽字符静态库依赖链：libncursesw -> libpanelw/menuw/formw -> libncursesw
            self.run(f"{cc} -o {bin_path} {src} {inc_flags} {lib_flags} -lncursesw", env="conanbuild")
            self.run(bin_path, env="conanrun")
