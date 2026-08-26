#!/usr/bin/env python3
"""Conan recipe for execline 2.9.9.2 — skarnet.org non-interactive scripting language.

execline uses skarnet's own configure + make system (NOT standard autotools
or cmake). It depends on skalibs (build-time + run-time). The configure script
needs explicit --with-sysdeps / --with-include / --with-lib pointing to the
skalibs package folder.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ExeclineConan(ConanFile):
    name = "execline"
    version = "2.9.9.2"
    description = "skarnet.org execline — non-interactive scripting language (libexecline + command-line tools)"
    license = "ISC"
    homepage = "https://skarnet.org/software/execline/"
    url = ""

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"

    options = {"shared": [True, False]}
    default_options = {"shared": False}

    # R26: static build by default (execline links statically against skalibs)

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("skalibs/2.15.1.0")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # skarnet configure is NOT standard autotools — do not use AutotoolsToolchain.
        # R33: do NOT use ${CC}/${CFLAGS} shell variables; the skarnet configure
        #      script reads CC/CFLAGS from the environment that Conan's build env
        #      already populates (profile [buildenv] + VirtualBuildEnv). We rely on
        #      the conanbuild env which sets CC/CFLAGS correctly for the OHOS toolchain.

        src = self.source_folder
        prefix = self.package_folder

        # Obtain skalibs package folder from the resolved dependency.
        # skalibs package layout:
        #   lib/libskarnet.a           (static library)
        #   lib/skalibs/sysdeps/       (sysdeps directory for configure)
        #   include/skalibs/*.h        (headers)
        # --with-lib must point to the directory containing libskarnet.a,
        # which is {prefix}/lib (NOT lib/skalibs — that only has sysdeps).
        # The skarnet Makefile uses "vpath lib%.a <dirs>" to locate the .a file.
        skalibs = self.dependencies["skalibs"]
        skalibs_prefix = skalibs.package_folder
        skalibs_sysdeps = os.path.join(skalibs_prefix, "lib", "skalibs", "sysdeps")
        skalibs_include = os.path.join(skalibs_prefix, "include")
        skalibs_lib = os.path.join(skalibs_prefix, "lib")

        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"execline does not support os={self.settings.os}"
            )

        configure_cmd = (
            f"cd {src} && ./configure"
            f" --prefix={prefix}"
            f" --disable-shared"
            f" --with-sysdeps={skalibs_sysdeps}"
            f" --with-include={skalibs_include}"
            f" --with-lib={skalibs_lib}"
        )
        self.run(configure_cmd, env="conanbuild")
        # R9: use -j1 (skarnet build order matters; execline has internal ordering)
        self.run(f"cd {src} && make -j1", env="conanbuild")
        self.run(f"cd {src} && make install", env="conanbuild")

    def package(self):
        # make install already places files into package_folder (prefix).
        # The skarnet configure --prefix points to self.package_folder, so
        # make install writes lib/libexecline.a, include/execline/*.h, and
        # bin/* executables directly into the package folder.
        pass

    def package_info(self):
        self.cpp_info.libs = ["execline"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        # execline also produces command-line executables (execlineb, define, exec, etc.)
        self.cpp_info.bindirs = ["bin"]
