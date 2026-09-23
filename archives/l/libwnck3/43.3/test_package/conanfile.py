#!/usr/bin/env python3
"""Build and execute a real libwnck consumer."""

import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.gnu import PkgConfigDeps


class Libwnck3TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        pkg_config = PkgConfigDeps(self)
        pkg_config.set_property("libwnck3", "pkg_config_name", "libwnck-3.0")
        pkg_config.set_property("glib", "pkg_config_name", "glib-2.0")
        pkg_config.set_property("gtk", "pkg_config_name", "gtk+-3.0")
        pkg_config.set_property("cairo", "pkg_config_name", "cairo")
        pkg_config.set_property("libx11", "pkg_config_name", "x11")
        pkg_config.set_property("libxres", "pkg_config_name", "xres")
        pkg_config.set_property("libxi", "pkg_config_name", "xi")
        pkg_config.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        executable = os.path.join(self.cpp.build.bindirs[0], "test_libwnck3")
        if cross_building(self) or str(self.settings.os) == "OHOS":
            qemu = next(
                (
                    candidate
                    for candidate in (
                        "/usr/bin/qemu-aarch64-static",
                        "/usr/bin/qemu-aarch64",
                        shutil.which("qemu-aarch64-static"),
                        shutil.which("qemu-aarch64"),
                    )
                    if candidate and os.path.isfile(candidate)
                ),
                None,
            )
            root = os.environ.get(
                "LIBWNCK_QEMU_ROOT",
                os.path.expanduser("~/.local/share/ohpcd/alpine-aarch64-3.24.0"),
            )
            shim = os.environ.get(
                "LIBWNCK_QEMU_SHIM",
                os.path.expanduser("~/.local/share/ohpcd/libwnck-qemu-runtime-shim.so"),
            )
            if qemu and os.path.isdir(root) and os.path.isfile(shim):
                libdirs = [os.path.join(root, "lib"), os.path.join(root, "usr", "lib")]
                for dependency in self.dependencies.values():
                    if dependency.package_folder:
                        candidate = os.path.join(dependency.package_folder, "lib")
                        if os.path.isdir(candidate):
                            libdirs.append(candidate)
                compilers = self.conf.get(
                    "tools.build:compiler_executables", default={}, check_type=dict
                ) or {}
                compiler = os.path.realpath(compilers.get("c", ""))
                native_root = compiler.partition("/native/llvm/bin/")[0]
                sdk_lib = os.path.join(
                    native_root, "native", "llvm", "lib", "aarch64-linux-ohos"
                )
                if os.path.isdir(sdk_lib):
                    libdirs.append(sdk_lib)
                command = [qemu, "-L", root,
                           "-E", "LD_LIBRARY_PATH=" + ":".join(libdirs),
                           "-E", "LD_PRELOAD=" + shim, executable]
                self.run(shlex.join(command))
                return
        self.run(executable, env="conanrun")
