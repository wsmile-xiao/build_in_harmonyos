#!/usr/bin/env python3
"""Conan recipe for brandy 1.23.6 (Matrix Brandy — BBC BASIC VI interpreter).

CMake build producing two CLI executables: sbrandy (simple-text UI) and
tbrandy (text-only UI).  The optional SDL 1.2 graphics front-end (brandy)
is disabled on OHOS: SDL 1.2 is not available in the conan registry, and
the CMakeLists guards it behind find_package(SDL 1.2) — the interpreter
core (sbrandy/tbrandy) needs no external dependency at all (m/dl/pthread/rt
only), so 方案 A (关闭可选特性) keeps full functionality.

Upstream tests: CMake registers "Regressions" (prove --exec sbrandy -r t/);
t/01count.t carries 3 TAP assertions and passes when run from the source
directory (the registered ctest command itself fails only because prove
resolves the relative "t/" against the build dir — an upstream invocation
quirk, not a test failure).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class BrandyConan(ConanFile):
    name = "brandy"
    version = "1.23.6"
    package_type = "application"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/stardot/MatrixBrandy"
    url = "https://github.com/stardot/MatrixBrandy"
    description = ("Matrix Brandy — free BBC BASIC VI interpreter "
                   "(sbrandy/tbrandy CLI)")

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        # 手动复制产物，绕开 cmake.install() 在 CI 干净环境下的 libc++ 加载挂起
        # （badvpn 同款方案：install 子进程会 re-spawn 动态加载 libc++_shared.so，
        #   CI 无本地 LD_LIBRARY_PATH 注入时无限等待，14400s 超时被杀）
        import shutil
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        for exe in ("sbrandy", "tbrandy"):
            shutil.copy2(os.path.join(self.build_folder, exe),
                         os.path.join(bin_dir, exe))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.conf_info.define("user.brandy:exe", os.path.join(
            self.package_folder, "bin", "sbrandy"))
