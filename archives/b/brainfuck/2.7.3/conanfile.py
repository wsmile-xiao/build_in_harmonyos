#!/usr/bin/env python3
"""Conan recipe for brainfuck 2.7.3 — CMake build system.

brainfuck is a Brainfuck interpreter written in C, providing both a
C API (libbrainfuck) and a command-line interpreter (brainfuck).

Build: cmake configure && cmake build && cmake install
"""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches


class BrainfuckConan(ConanFile):
    name = "brainfuck"
    version = "2.7.3"
    description = "Brainfuck interpreter written in C"
    license = "Apache-2.0"
    homepage = "https://github.com/fabianishere/brainfuck"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def validate(self):
        # R32: OHOS 平台兼容 — settings.os 判断必须包含 "OHOS"
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"brainfuck only supports Linux/OHOS, got {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _sysroot_include(self):
        """Locate the toolchain sysroot usr/include (contains getopt.h).

        Findgetopt.cmake's find_path() does not search the compiler's
        builtin sysroot, so it falls back to the bundled deps/getopt
        (Windows wingetopt shim that #includes <windows.h>) and fails.
        Probe the compiler's include search list instead (R33: compiler
        comes from Conan conf, not shell env).
        """
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c") if compilers else None
        if not cc:
            return None
        try:
            r = subprocess.run(
                [cc, "-E", "-v", "-x", "c", os.devnull],
                capture_output=True, text=True, timeout=60,
            )
            in_search = False
            for line in (r.stderr or "").splitlines():
                if "search starts here" in line:
                    in_search = True
                    continue
                if in_search:
                    stripped = line.strip()
                    if not stripped or stripped == "End of search list.":
                        break
                    if stripped.endswith("/usr/include"):
                        return stripped
        except Exception:
            pass
        return None

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: static linking by default for the library
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # OHOS has no editline library; the interactive console is optional
        tc.variables["ENABLE_EDITLINE"] = "OFF"
        tc.variables["ENABLE_CLI"] = "ON"
        tc.variables["BUILD_TESTING"] = "OFF"
        # Point getopt lookup at the toolchain sysroot (see _sysroot_include)
        sysroot_inc = self._sysroot_include()
        if sysroot_inc:
            tc.variables["GETOPT_INCLUDE_DIR"] = sysroot_inc
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # 上游 CMakeLists.txt 未安装公共头文件 (install(TARGETS) 仅装库与
        # EXPORT 接口，INSTALL_INTERFACE 引用 include/ 但无 install(FILES))，
        # 必须补充安装，否则下游 find_package 的 INTERFACE_INCLUDE_DIRECTORIES
        # 指向不存在的路径。
        copy(self, "include/brainfuck.h", src=self.source_folder, dst=self.package_folder)

    def package_info(self):
        self.cpp_info.libs = ["brainfuck"]
