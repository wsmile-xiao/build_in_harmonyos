#!/usr/bin/env python3
"""Conan recipe for libsigc++ 2.12.1 (Meson)."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class _PosixPrefixMeson(Meson):
    @property
    def _prefix(self):
        # Conan derives C:/ from the Windows build machine, but Meson validates
        # this value for the OHOS target. Installation remains isolated by
        # Meson's --destdir argument in Meson.install().
        return "/"


class LibsigcConan(ConanFile):
    name = "libsigc"
    version = "2.12.1"
    description = "Typesafe callback system for standard C++"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/libsigcplusplus/libsigcplusplus"
    url = "https://github.com/libsigcplusplus/libsigcplusplus"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libsigc supports Linux and OHOS targets, got {self.settings.os}"
            )
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        if self.settings.os == "OHOS" and self.settings_build.os == "Windows":
            self._configure_ohos_toolchain(tc)
        tc.project_options["default_library"] = (
            "shared" if self.options.shared else "static"
        )
        tc.project_options["maintainer-mode"] = "false"
        tc.project_options["build-documentation"] = "false"
        tc.project_options["validation"] = "false"
        tc.project_options["build-pdf"] = "false"
        tc.project_options["build-examples"] = "false"
        tc.project_options["build-tests"] = "true"
        tc.project_options["benchmark"] = "false"
        tc.project_options["wrap_mode"] = "nodownload"
        tc.generate()
        self._inject_meson_archiver()

    def _configure_ohos_toolchain(self, tc):
        if self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                f"libsigc supports OHOS armv8, got {self.settings.arch}"
            )
        executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        compiler = executables.get("cpp") or executables.get("c") or ""
        llvm_root = os.path.dirname(os.path.dirname(compiler))
        sdk_native = os.path.dirname(llvm_root)
        sysroot = os.path.join(sdk_native, "sysroot")
        if not compiler or not os.path.isdir(sysroot):
            raise ConanInvalidConfiguration(
                "OHOS Meson cross-build requires the SDK compiler and sysroot "
                "from tools.build:compiler_executables"
            )
        target_flags = [
            "--target=aarch64-linux-ohos",
            "--sysroot={}".format(sysroot.replace("\\", "/")),
        ]
        tc.c_args.extend(target_flags + ["-D__MUSL__"])
        tc.cpp_args.extend(target_flags + ["-D__MUSL__"])
        tc.c_link_args.extend(target_flags)
        tc.cpp_link_args.extend(target_flags)

    def _inject_meson_archiver(self):
        executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        ar = executables.get("ar")
        ranlib = executables.get("ranlib")
        if not ar:
            compiler = executables.get("cpp") or executables.get("c") or ""
            bindir = os.path.dirname(compiler)
            suffix = ".exe" if os.name == "nt" else ""
            candidate = os.path.join(bindir, "llvm-ar" + suffix) if bindir else ""
            if candidate and os.path.isfile(candidate):
                ar = candidate
                candidate_ranlib = os.path.join(bindir, "llvm-ranlib" + suffix)
                if os.path.isfile(candidate_ranlib):
                    ranlib = candidate_ranlib

        machine_file = next(
            (
                os.path.join(self.generators_folder, filename)
                for filename in (
                    "conan_meson_cross.ini",
                    "conan_meson_native.ini",
                )
                if os.path.isfile(os.path.join(self.generators_folder, filename))
            ),
            None,
        )
        if not ar or not machine_file:
            return
        with open(machine_file, encoding="utf-8") as handle:
            content = handle.read()
        if "\nar =" in content or "[binaries]" not in content:
            return
        binaries = "[binaries]\nar = '{}'\n".format(ar.replace("\\", "/"))
        if ranlib:
            binaries += "ranlib = '{}'\n".format(ranlib.replace("\\", "/"))
        with open(machine_file, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content.replace("[binaries]\n", binaries, 1))

    def build(self):
        meson = _PosixPrefixMeson(self)
        meson.configure()
        meson.build()
        if can_run(self):
            meson.test()
        else:
            self.output.info(
                "cross-building: 32 upstream tests compiled but cannot run"
            )

    def package(self):
        _PosixPrefixMeson(self).install()
        self._materialize_shared_library_aliases()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def _materialize_shared_library_aliases(self):
        if not self.options.shared:
            return
        libdir = os.path.join(self.package_folder, "lib")
        versioned = os.path.join(libdir, "libsigc-2.0.so.0.0.0")
        if not os.path.isfile(versioned):
            raise RuntimeError(f"Missing installed shared library: {versioned}")
        for alias in ("libsigc-2.0.so.0", "libsigc-2.0.so"):
            destination = os.path.join(libdir, alias)
            if not os.path.exists(destination):
                shutil.copy2(versioned, destination)

    def package_info(self):
        self.cpp_info.libs = ["sigc-2.0"]
        self.cpp_info.includedirs = [
            os.path.join("include", "sigc++-2.0"),
            os.path.join("lib", "sigc++-2.0", "include"),
        ]
        self.cpp_info.set_property("cmake_file_name", "libsigc")
        self.cpp_info.set_property("cmake_target_name", "libsigc::libsigc")
        self.cpp_info.set_property("pkg_config_name", "sigc++-2.0")
