#!/usr/bin/env python3
"""Conan recipe for lizard 2.1."""

import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LizardConan(ConanFile):
    name = "lizard"
    version = "2.1"
    description = "Fast lossless compression library and command line tool"
    license = "BSD-2-Clause AND GPL-2.0-or-later"
    homepage = "https://github.com/inikep/lizard"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        args = self._make_args()
        lib_target = "liblizard" if self.options.shared else "liblizard.a"
        self.run(f"make -j1 -C lib {args} {lib_target}", cwd=self.source_folder)
        self.run(f"make -j1 -C programs {args} lizard", cwd=self.source_folder)
        if can_run(self):
            self.run(f"make -j1 -C examples {args} test", cwd=self.source_folder)

    def package(self):
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        for header in (
            "lizard_compress.h",
            "lizard_decompress.h",
            "lizard_common.h",
            "lizard_frame.h",
        ):
            copy(
                self,
                header,
                src=os.path.join(self.source_folder, "lib"),
                dst=os.path.join(self.package_folder, "include"),
                keep_path=False,
            )
        copy(
            self,
            "mem.h",
            src=os.path.join(self.source_folder, "lib", "entropy"),
            dst=os.path.join(self.package_folder, "include", "entropy"),
            keep_path=False,
        )

        if self.options.shared:
            copy(
                self,
                "liblizard.so*",
                src=os.path.join(self.source_folder, "lib"),
                dst=os.path.join(self.package_folder, "lib"),
                keep_path=False,
            )
        else:
            copy(
                self,
                "liblizard.a",
                src=os.path.join(self.source_folder, "lib"),
                dst=os.path.join(self.package_folder, "lib"),
                keep_path=False,
            )

        binary = "lizard.exe" if str(self.settings.os) == "Windows" else "lizard"
        copy(
            self,
            binary,
            src=os.path.join(self.source_folder, "programs"),
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["lizard"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "lizard")
        self.cpp_info.set_property("cmake_target_name", "lizard::lizard")
        self.cpp_info.set_property("pkg_config_name", "lizard")

    def _make_args(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = executables.get("c") or os.environ.get("CC") or "clang"
        ar = executables.get("ar") or self._tool_next_to(cc, "llvm-ar") or "llvm-ar"
        optimization = "-O0 -g" if str(self.settings.build_type) == "Debug" else "-O3"
        cflags = f"{optimization} -fPIC"
        return " ".join(
            [
                f"CC={shlex.quote(cc)}",
                f"AR={shlex.quote(ar)}",
                f"CFLAGS={shlex.quote(cflags)}",
            ]
        )

    @staticmethod
    def _tool_next_to(compiler, tool):
        bindir = os.path.dirname(compiler) if os.path.isabs(compiler) else ""
        candidate = os.path.join(bindir, tool) if bindir else ""
        return candidate if candidate and os.path.isfile(candidate) else ""
