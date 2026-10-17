#!/usr/bin/env python3
"""Conan recipe — concalc 0.9.3 (CMake).

concalc is the console version of the Extcalc scientific calculator: a small
C++ CLI that evaluates expressions given as command line arguments.

Upstream's CMakeLists.txt declares CMAKE_MINIMUM_REQUIRED(VERSION 2.4.3);
CMake >= 4 refuses anything below 3.5, so configure() passes
-DCMAKE_POLICY_VERSION_MINIMUM=3.5 (a pure build-invocation fix — no upstream
source change needed).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class ConcalcConan(ConanFile):
    name = "concalc"
    version = "0.9.3"
    description = "Scientific calculator for the terminal (console version of Extcalc)"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/extcalc-linux/"
    url = "https://sourceforge.net/projects/extcalc-linux/"
    topics = ("calculator", "console", "math", "scientific")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libc/libstdc++ only — no third-party dependencies.
        pass

    def validate(self):
        # R32: OHOS must be matched alongside Linux, never `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"concalc supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 上游 CMAKE_MINIMUM_REQUIRED(VERSION 2.4.3)：cmake >= 4 拒绝 < 3.5，
        # 用官方迁移变量放行（不改上游源码，R33 精神：构建注入而非改源）。
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # CMakeLists 只装 bin/concalc 与 man 页；把许可证/说明一并带上。
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        copy(self, "README", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # HarmonyOS XPM 要求被 exec 的 ELF 自签；hnp 工具链自带 libc++ 解析依赖
        # 自身所在路径，profile buildenv 前置的 SDK llvm/lib LD_LIBRARY_PATH 会
        # 遮蔽它（"Error relocating ... symbol not found"），故用 env -u 清除。
        if self.settings.os != "OHOS":
            return
        import glob
        targets = glob.glob(os.path.join(self.package_folder, "bin", "*"))
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if not os.path.isfile(f) or os.path.islink(f) or not self._is_elf(f):
                continue
            self.run('env -u LD_LIBRARY_PATH {oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('env -u LD_LIBRARY_PATH {sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.libs = []  # concalc is a CLI tool, it ships no library
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]

# CMakeToolchain import is needed by generate(); placed here to keep the
# header clean per repository style seen in neighbouring recipes.
from conan.tools.cmake import CMakeToolchain
