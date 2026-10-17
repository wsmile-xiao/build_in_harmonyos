#!/usr/bin/env python3
"""Conan recipe for proxy-libintl 0.5."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import (
    check_sha256,
    copy,
    get,
    unzip,
)
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class ProxyLibintlConan(ConanFile):
    name = "proxy-libintl"
    version = "0.5"
    description = "Minimal gettext-compatible proxy library"
    license = "LGPL-2.0-or-later"
    homepage = "https://github.com/frida/proxy-libintl"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                "proxy-libintl's OHOS adaptation is validated only for armv8/AArch64"
            )
        if self.settings.os == "OHOS" and self.options.shared:
            raise ConanInvalidConfiguration(
                "proxy-libintl must be static on OHOS to avoid conflicting with "
                "the platform libintl shared library"
            )

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        local_archive = self.conf.get(
            "user.proxy-libintl:source_archive", default=None
        )
        if local_archive:
            if not os.path.isfile(local_archive):
                raise ConanInvalidConfiguration(
                    "user.proxy-libintl:source_archive does not name a regular file"
                )
            check_sha256(
                self,
                local_archive,
                self.conan_data["sources"][str(self.version)]["sha256"],
            )
            unzip(
                self,
                local_archive,
                destination=self.source_folder,
                strip_root=True,
            )
            return
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        toolchain = MesonToolchain(self)
        toolchain.project_options["default_library"] = (
            "shared" if self.options.shared else "static"
        )
        toolchain.project_options["wrap_mode"] = "nodownload"
        toolchain.generate()

        if self.settings.os == "OHOS":
            compilers = self.conf.get(
                "tools.build:compiler_executables",
                default={},
                check_type=dict,
            ) or {}
            cc = compilers.get("c") or ""
            tool_dir = os.path.dirname(cc) if os.path.isabs(cc) else ""
            compiler_name = os.path.basename(cc)
            suffix = (
                compiler_name[len("clang"):]
                if compiler_name.startswith("clang")
                else ""
            )

            ar = compilers.get("ar")
            ranlib = compilers.get("ranlib")
            if tool_dir:
                ar = ar or os.path.join(tool_dir, f"llvm-ar{suffix}")
                ranlib = ranlib or os.path.join(tool_dir, f"llvm-ranlib{suffix}")

            for name, path in (("ar", ar), ("ranlib", ranlib)):
                if not path or not os.path.isabs(path) or not os.path.isfile(path):
                    raise ConanInvalidConfiguration(
                        f"OHOS Meson builds require an absolute {name} executable "
                        "from tools.build:compiler_executables or the C compiler "
                        "directory"
                    )

            toolchain_file = os.path.join(
                self.generators_folder,
                (
                    "conan_meson_cross.ini"
                    if cross_building(self)
                    else "conan_meson_native.ini"
                ),
            )
            if not os.path.isfile(toolchain_file):
                raise ConanInvalidConfiguration(
                    "MesonToolchain did not generate the expected machine file"
                )
            with open(toolchain_file, encoding="utf-8") as stream:
                content = stream.read()
            if "[binaries]\n" not in content:
                raise ConanInvalidConfiguration(
                    "Meson native file has no [binaries] section"
                )
            entries = ""
            if "\nar =" not in content:
                entries += f"ar = '{ar.replace(os.sep, '/')}'\n"
            if "\nranlib =" not in content:
                entries += f"ranlib = '{ranlib.replace(os.sep, '/')}'\n"
            if entries:
                content = content.replace(
                    "[binaries]\n", f"[binaries]\n{entries}", 1
                )
                with open(
                    toolchain_file, "w", encoding="utf-8", newline="\n"
                ) as stream:
                    stream.write(content)

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        Meson(self).install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["intl"]
        if not self.options.shared:
            self.cpp_info.defines.append("G_INTL_STATIC_COMPILATION")
        self.cpp_info.set_property("cmake_file_name", "proxy-libintl")
        self.cpp_info.set_property("cmake_target_name", "proxy-libintl::intl")
        self.cpp_info.set_property("pkg_config_name", "intl")
