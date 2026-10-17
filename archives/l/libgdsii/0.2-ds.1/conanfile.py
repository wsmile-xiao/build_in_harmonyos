#!/usr/bin/env python3
"""Conan recipe for libGDSII - C++ reader for GDSII geometry files.

Autotools project (libtool, static-only via AC_DISABLE_SHARED). The GitHub
tag archive ships no generated `configure`, so build() bootstraps with
`autoreconf -fi`; automake/aclocal/libtoolize come in via tool_requires
because the CI sandbox only ships the autoconf suite (argp-standalone
precedent). configure/make/install are invoked through
`env -u CONFIG_SHELL SHELL=/bin/sh` - the OHOS conan profile points
SHELL/CONFIG_SHELL at the getcwd-broken hnp bash (E386 family).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, replace_in_file
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout

SH = "env -u CONFIG_SHELL SHELL=/bin/sh"
CONFIGURE_ARGS = (
    "--prefix=/"
    " '--libdir=${prefix}/lib'"
    " '--includedir=${prefix}/include'"
    " --with-pic"
    " --disable-shared --enable-static"
    " --build=aarch64-unknown-linux-gnu"
    " --host=aarch64-unknown-linux-gnu"
)


class LibgdsiiConan(ConanFile):
    name = "libgdsii"
    version = "0.2-ds.1"
    description = "libGDSII - C++ library for reading GDSII geometry files"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/HomerReid/libGDSII"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # The tag archive ships no `configure`: build() runs `autoreconf -fi`.
        # The build host (CI sandbox / minimal OHOS image) lacks
        # automake/aclocal/libtoolize, so pull them in as tool_requires
        # (same approach as argp-standalone).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4.1")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 2019-era config.sub does not know the linux-ohos triplet; treat as
        # a native aarch64 build (units/direvent precedent).
        tc.configure_args.extend([
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
        ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        src = self.source_folder

        # The tag archive ships no generated `configure`: bootstrap one.
        # autoreconf itself must not see the getcwd-broken hnp bash either.
        self.run(SH + " autoreconf -fi", cwd=src, env="conanbuild")

        # E011/E114: HMDFS makes the umask-077 config.status temp dir
        # unwritable - relax to 002 (direvent/gtypist precedent).
        replace_in_file(self, os.path.join(src, "configure"),
                        "umask 077", "umask 002")

        self.run('cd "' + src + '" && ' + SH + " sh configure " + CONFIGURE_ARGS)
        self.run('cd "' + src + '" && ' + SH + " make -j1")

    def package(self):
        src = self.source_folder
        self.run('cd "' + src + '" && ' + SH + ' make install DESTDIR="'
                 + self.package_folder + '/"')

        # The package ships the static library + headers only; the example
        # binary (GDSIIConvert) and the libtool archive are out of scope.
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            shutil.rmtree(bindir)
        libdir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(libdir):
            for name in os.listdir(libdir):
                # Ship the static library only (AC_DISABLE_SHARED turned out
                # not to be honoured by the libtool 2.5.4 in-tree regeneration,
                # so strip any .so/.la leftovers explicitly).
                if name.endswith(".la") or ".so" in name:
                    os.remove(os.path.join(libdir, name))

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["GDSII"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
