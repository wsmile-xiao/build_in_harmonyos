#!/usr/bin/env python3
"""Conan recipe — game-music-emu 0.6.5（LGPL-2.1 CMake 库，鸿蒙 PC aarch64 移植）。

上游: https://github.com/libgme/game-music-emu (tag 0.6.5)
依赖: zlib/1.3.2（上游 GME_ZLIB 默认开启，VGZ 压缩格式需要；基线已提供）
上游测试: 2 个 CTest（sanity_test_NSF + check_proper_NSF_output），在 build()
          的独立临时目录中以静态配置构建并运行；另跑 demo_mem/demo_multi 冒烟。
适配点: test/checksums 移除 # 注释行（toybox sha256sum -c 不支持注释）。
"""
import os
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class GameMusicEmuConan(ConanFile):
    name = "game-music-emu"
    version = "0.6.5"
    description = "Multi-format video game music emulation library (NSF/GBS/VGM/SPC/...)"

    license = "LGPL-2.1"
    homepage = "https://github.com/libgme/game-music-emu"
    url = ""  # CI fills this

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # VGZ/VGM 压缩格式需要 zlib；上游 GME_ZLIB 选项默认开启
        self.requires("zlib/1.3.2")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            arch_map = {"armv8": "aarch64", "x86_64": "x86_64"}
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = arch_map.get(
                str(self.settings.arch), str(self.settings.arch)
            )
        tc.cache_variables["GME_ZLIB"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        variables = {
            "GME_BUILD_SHARED": "ON" if self.options.shared else "OFF",
            "GME_BUILD_STATIC": "OFF" if self.options.shared else "ON",
            "GME_BUILD_TESTING": "OFF",   # 上游测试在独立目录运行
            "GME_BUILD_EXAMPLES": "OFF",  # 主构建不编译 demo/player
        }
        cmake.configure(variables=variables)
        cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """上游测试独立构建目录（固定静态配置），与主构建互不干扰。"""
        test_build_dir = tempfile.mkdtemp(prefix="gme-tests-")
        try:
            toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake").replace("\\", "/")
            cmake_cmd = [
                "cmake", self.source_folder,
                "-G", "Unix Makefiles",
                "-DCMAKE_TOOLCHAIN_FILE=" + toolchain,
                "-DGME_BUILD_TESTING=ON",
                "-DGME_BUILD_EXAMPLES=ON",
                "-DGME_BUILD_SHARED=OFF",
                "-DGME_BUILD_STATIC=ON",
            ]
            run_tests = True
            if self.settings.os == "OHOS":
                cmake_cmd.append("-DCMAKE_EXE_LINKER_FLAGS=-static")
                if cross_building(self):
                    qemu = shutil.which("qemu-aarch64")
                    if qemu:
                        cmake_cmd.append("-DCMAKE_CROSSCOMPILING_EMULATOR=" + qemu)
                    else:
                        run_tests = False
                        self.output.warning(
                            "qemu-aarch64 not found; skipping upstream test execution"
                        )
            subprocess.check_call(cmake_cmd, cwd=test_build_dir)
            # demo 目标是 EXCLUDE_FROM_ALL，须显式构建
            subprocess.check_call(
                ["cmake", "--build", ".", "--target", "demo", "demo_mem", "demo_multi", "-j2"],
                cwd=test_build_dir,
            )
            if not run_tests:
                return
            # 上游注册的 2 个 CTest 测试
            subprocess.check_call(["ctest", "--output-on-failure"], cwd=test_build_dir)
            # 额外冒烟：demo_mem（VGZ→zlib 路径）、demo_multi（多通道 API）
            demo_dir = os.path.join(test_build_dir, "demo")
            for exe in ("demo_mem", "demo_multi"):
                subprocess.check_call([os.path.join(demo_dir, exe)], cwd=demo_dir)
        finally:
            shutil.rmtree(test_build_dir, ignore_errors=True)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "license.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["gme"]
        self.cpp_info.requires = ["zlib::zlib"]
        self.cpp_info.set_property("cmake_file_name", "game-music-emu")
        self.cpp_info.set_property("cmake_target_name", "gme::gme")
        self.cpp_info.set_property("pkg_config_name", "libgme")
