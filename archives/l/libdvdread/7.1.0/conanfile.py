#!/usr/bin/env python3
"""Conan recipe for libdvdread 7.1.0."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibdvdreadConan(ConanFile):
    name = "libdvdread"
    version = "7.1.0"
    description = "Low-level DVD access library"
    license = "GPL-2.0-or-later"
    homepage = "https://www.videolan.org/developers/libdvdnav.html"
    url = "https://code.videolan.org/videolan/libdvdread"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if bool(self.options.shared):
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            filename="libdvdread-7.1.0.tar.xz",
            strip_root=True,
        )

    def generate(self):
        toolchain = MesonToolchain(self)
        if (
            str(self.settings.os) == "OHOS"
            and self.settings_build.os == "Windows"
        ):
            self._configure_windows_ohos_toolchain(toolchain)
        toolchain.project_options["default_library"] = (
            "shared" if bool(self.options.shared) else "static"
        )
        toolchain.project_options["enable_docs"] = False
        toolchain.project_options["libdvdcss"] = "disabled"
        toolchain.generate()
        self._inject_meson_archive_tools()

    def _configure_windows_ohos_toolchain(self, toolchain):
        targets = {
            "armv8": "aarch64-linux-ohos",
            "x86_64": "x86_64-linux-ohos",
        }
        target = targets.get(str(self.settings.arch))
        executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        compiler = executables.get("c") or executables.get("cpp") or ""
        llvm_root = os.path.dirname(os.path.dirname(compiler))
        sdk_native = os.path.dirname(llvm_root)
        sysroot = os.path.join(sdk_native, "sysroot")
        if not target or not compiler or not os.path.isdir(sysroot):
            raise ConanInvalidConfiguration(
                "OHOS Meson cross-build requires a supported architecture "
                "and the DevEco SDK compiler/sysroot"
            )

        target_flags = [
            f"--target={target}",
            f"--sysroot={sysroot.replace(os.sep, '/')}",
        ]
        toolchain.c_args.extend(target_flags + ["-D__MUSL__"])
        toolchain.cpp_args.extend(target_flags + ["-D__MUSL__"])
        toolchain.c_link_args.extend(target_flags)
        toolchain.cpp_link_args.extend(target_flags)

    def _inject_meson_archive_tools(self):
        executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        compiler = executables.get("c") or executables.get("cpp") or ""
        bindir = os.path.dirname(compiler)
        suffix = ".exe" if os.name == "nt" else ""
        ar = executables.get("ar")
        ranlib = executables.get("ranlib")
        if not ar and bindir:
            candidate = os.path.join(bindir, f"llvm-ar{suffix}")
            if os.path.isfile(candidate):
                ar = candidate
        if not ranlib and bindir:
            candidate = os.path.join(bindir, f"llvm-ranlib{suffix}")
            if os.path.isfile(candidate):
                ranlib = candidate

        machine_file = next(
            (
                os.path.join(self.generators_folder, filename)
                for filename in (
                    "conan_meson_cross.ini",
                    "conan_meson_native.ini",
                )
                if os.path.isfile(
                    os.path.join(self.generators_folder, filename)
                )
            ),
            None,
        )
        if not ar or not machine_file:
            return

        with open(machine_file, encoding="utf-8") as handle:
            content = handle.read()
        if "\nar =" in content or "[binaries]" not in content:
            return
        archive_tools = (
            "[binaries]\n"
            f"ar = '{ar.replace(os.sep, '/')}'\n"
        )
        if ranlib:
            archive_tools += (
                f"ranlib = '{ranlib.replace(os.sep, '/')}'\n"
            )
        with open(
            machine_file,
            "w",
            encoding="utf-8",
            newline="\n",
        ) as handle:
            handle.write(
                content.replace("[binaries]\n", archive_tools, 1)
            )

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["dvdread"]
        self.cpp_info.set_property("cmake_file_name", "dvdread")
        self.cpp_info.set_property(
            "cmake_target_name", "dvdread::dvdread"
        )
        self.cpp_info.set_property("pkg_config_name", "dvdread")
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl"]
