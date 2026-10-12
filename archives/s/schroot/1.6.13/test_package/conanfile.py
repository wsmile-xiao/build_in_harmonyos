#!/usr/bin/env python3
"""test_package — schroot 消费者用例（显式测试：链接 libsbuild 的 C++ 程序 + CLI 检查）。"""

import os
from pathlib import Path

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import load


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 消费者要使用 sbuild 的公共头文件并链接包内 libsbuild.a，因此需要
        # boost/libuuid 的头文件与库；在消费者图中显式声明，否则它们的二进制
        # 会被跳过、取不到安装路径（实测：仅靠配方的转发依赖声明仍会被跳过）。
        self.requires("boost/1.84.0")
        self.requires("libuuid/2.40.4")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # schroot 的包只提供静态库与 pkg-config 文件（未导出 CMake 目标）；消费者
        # 用例按各依赖包内的实际安装路径取其头文件与库——sbuild 的公共头文件依赖
        # boost，链接包内 libsbuild.a 还需要 uuid/gettext/boost 等依赖库。
        include_dirs = []
        library_dirs = []
        libraries = []
        for dependency in self.dependencies.values():
            package_folder = dependency.package_folder
            if not package_folder:
                continue
            include_dir = Path(package_folder) / "include"
            if include_dir.is_dir() and str(include_dir) not in include_dirs:
                include_dirs.append(str(include_dir))
            lib_dir = Path(package_folder) / "lib"
            if not lib_dir.is_dir():
                continue
            if str(lib_dir) not in library_dirs:
                library_dirs.append(str(lib_dir))
            for lib in dependency.cpp_info.aggregated_components().libs:
                if lib in libraries:
                    continue
                candidates = ["lib{}.a".format(lib), "lib{}.so".format(lib)]
                if any((lib_dir / name).exists() for name in candidates):
                    libraries.append(lib)
        schroot_folder = Path(self.dependencies["schroot"].package_folder)
        toolchain = CMakeToolchain(self)
        toolchain.variables["SCHROOT_INCLUDE_DIRS"] = ";".join(include_dirs)
        toolchain.variables["SCHROOT_LIBRARY_DIRS"] = ";".join(library_dirs)
        toolchain.variables["SCHROOT_LIBRARIES"] = ";".join(libraries)
        toolchain.variables["SCHROOT_SBUILD_LIB"] = str(schroot_folder / "lib" / "libsbuild.a")
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        schroot = self.dependencies["schroot"]
        package_folder = schroot.package_folder
        bindir = schroot.cpp_info.bindirs[0] if schroot.cpp_info.bindirs else "bin"
        if not os.path.isabs(bindir):
            bindir = os.path.join(package_folder, bindir)
        exe = os.path.join(bindir, "schroot")
        assert os.path.isfile(exe), "schroot executable is missing from the package"

        if can_run(self):
            # 链接包内 libsbuild.a 的消费者程序
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "schroot_consumer"),
                env="conanrun",
            )

        # CLI 检查：直接从包目录执行安装产物（鸿蒙上安装副本的可执行性回归点）
        version_file = os.path.join(self.build_folder, "schroot-version.txt")
        self.run('"{}" --version > "{}"'.format(exe, version_file), env="conanrun")
        version = load(self, version_file)
        assert "schroot" in version and "1.6.13" in version, (
            "unexpected schroot --version output: {}".format(version.strip())
        )

        help_file = os.path.join(self.build_folder, "schroot-help.txt")
        self.run('"{}" --help > "{}"'.format(exe, help_file), env="conanrun")
        assert "session" in load(self, help_file), "schroot --help produced no session help"

        # 会话辅助程序必须随包提供（schroot 运行时会调用它们）
        for helper in ("schroot-mount", "schroot-listmounts"):
            helper_path = os.path.join(package_folder, "libexec", "schroot", helper)
            assert os.path.isfile(helper_path), "{} is missing from the package".format(helper)
