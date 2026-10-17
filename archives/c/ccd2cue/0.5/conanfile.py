#!/usr/bin/env python3
"""Conan recipe for GNU ccd2cue 0.5."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Ccd2CueConan(ConanFile):
    name = "ccd2cue"
    version = "0.5"
    description = "GNU CCD sheet to CUE sheet converter"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/ccd2cue/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} supports only Linux and OHOS, not {self.settings.os}"
            )
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def requirements(self):
        # GNU argp is not part of the OHOS/musl sysroot; use the published
        # static compatibility package instead of hiding a parser stub.
        self.requires("argp-standalone/1.5.0")

    def layout(self):
        basic_layout(self)
        # The release archive contains generated Autotools files and expects
        # configure/make products in the source tree.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    @staticmethod
    def _dependency_flags(dependencies):
        includes = []
        libdirs = []
        libs = []
        for _, dep in dependencies.items():
            cpp_info = dep.cpp_info
            package_folder = dep.package_folder or ""
            for include_dir in cpp_info.includedirs or []:
                path = include_dir if os.path.isabs(include_dir) else os.path.join(package_folder, include_dir)
                includes.append("-I" + path)
            for lib_dir in cpp_info.libdirs or []:
                path = lib_dir if os.path.isabs(lib_dir) else os.path.join(package_folder, lib_dir)
                libdirs.append("-L" + path)
            libs.extend("-l" + name for name in (cpp_info.libs or []))
        return includes, libdirs, libs

    def generate(self):
        tc = AutotoolsToolchain(self)
        # The patched config.guess/config.sub must select the native OHOS
        # triplet; profile-generated --build/--host overrides are removed.
        tc.configure_args = [
            arg for arg in tc.configure_args
            if not str(arg).startswith("--build=")
            and not str(arg).startswith("--host=")
        ]
        tc.configure_args.extend((
            "--disable-nls",
            "--disable-doxygen-doc",
            "--disable-doxygen-dot",
        ))

        includes, libdirs, _ = self._dependency_flags(self.dependencies.host)
        env = tc.environment()
        if includes:
            env.append("CPPFLAGS", includes)
        if libdirs:
            env.append("LDFLAGS", libdirs)
        tc.generate(env)

    def build(self):
        apply_conandata_patches(self)

        # Autoconf's generated config.status creates 0700 temporary folders;
        # HMDFS rejects files inside them. Keep this as a build-time repair so
        # the generated configure script itself is not committed as a patch.
        configure = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure):
            replace_in_file(self, configure, "umask 077", "umask 022", strict=False)

        for relative in (
            "configure",
            "build-aux/config.guess",
            "build-aux/config.sub",
            "build-aux/install-sh",
            "build-aux/missing",
        ):
            path = os.path.join(self.source_folder, relative)
            if os.path.isfile(path):
                os.chmod(path, os.stat(path).st_mode | 0o111)

        _, _, libs = self._dependency_flags(self.dependencies.host)
        autotools = Autotools(self)
        # Keep LIBS out of the toolchain environment during generic configure
        # probes; pass it as a configure variable so the final link receives
        # the real argp implementation without a shell-global dependency.
        autotools.configure(args=["LIBS=" + " ".join(libs)])
        autotools.make(args=["-j1"])
        autotools.make(target="check", args=["-j1"])

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        copy(self, "ccd2cue", src=os.path.join(self.source_folder, "src"), dst=bin_dir)
        copy(
            self,
            "ccd2cue.1",
            src=os.path.join(self.source_folder, "doc", "man"),
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        binary = os.path.join(bin_dir, "ccd2cue")
        if os.path.isfile(binary):
            os.chmod(binary, os.stat(binary).st_mode | 0o111)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
