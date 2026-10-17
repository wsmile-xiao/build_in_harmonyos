#!/usr/bin/env python3
"""Conan recipe for libimobiledevice 1.4.0 (Autotools).

libimobiledevice ecosystem: iOS device communication library
(libimobiledevice-1.0) plus the idevice* CLI tools.  Version 1.4.0 split
the former common/ utilities out into libimobiledevice-glue and added the
TSS client libtatsu, both of which are already published on ohpcd.

Dependencies (all from the ohpcd registry):
  - libplist/2.3.0           (>= 2.3.0 per configure.ac)
  - libusbmuxd/2.0.2         (>= 2.0.2 per configure.ac)
  - libimobiledevice-glue/1.3.0 (>= 1.3.0 per configure.ac)
  - libtatsu/1.0.5           (>= 1.0.3 per configure.ac)
  - openssl/1.1.1w           (default ssl backend, PKG_CHECK "openssl >= 0.9.8")

OHOS adaptations - all pitfalls already flattened by the 1.3.0 sibling and
the libimobiledevice-glue/libtatsu recipes (knowledge base E114 family,
E011 umask, .la rename, make -j1):
  - mktemp wrapper returning failure so autoconf AS_TMPDIR falls back to
    mkdir (HMDFS mktemp -d perms break config.status, E114).
  - "umask 077" -> "umask 022" in the shipped configure (E011 family).
  - --build=aarch64-unknown-linux-gnu (config.guess does not know OHOS).
  - rename dependency *.la files (conan prefix makes libdir='//lib'
    invalid for libtool, "not a valid libtool archive").
  - make -j1 (HMDFS jobserver fifo EPERM).
  - --without-cython: no Python bindings on OHOS.
"""
import glob
import os
import stat
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get, replace_in_file)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibimobiledeviceConan(ConanFile):
    name = "libimobiledevice"
    version = "1.4.0"
    description = "Library to communicate with iOS devices (libimobiledevice ecosystem)"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/libimobiledevice/libimobiledevice"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libimobiledevice is only supported on Linux/OHOS, not %s"
                % self.settings.os)

    def requirements(self):
        self.requires("libplist/2.3.0")
        self.requires("libusbmuxd/2.0.2")
        self.requires("libimobiledevice-glue/1.3.0")
        self.requires("libtatsu/1.0.5")
        self.requires("openssl/1.1.1w")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # E114 family: autoconf AS_TMPDIR uses `umask 077 && mktemp -d`,
        # which on HMDFS creates dirs config.status cannot write into.
        # A fake mktemp returning failure forces the mkdir fallback.
        wrapper_dir = Path(self.build_folder) / ".hmos_fix"
        wrapper_dir.mkdir(exist_ok=True)
        wrapper = wrapper_dir / "mktemp"
        wrapper.write_text(
            '#!/bin/sh\n'
            '# HarmonyOS: mktemp -d creates dirs with broken perms (hmmac MAC).\n'
            '# Return failure to force autoconf AS_TMPDIR to use mkdir fallback.\n'
            'exit 1\n'
        )
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC)

        # Dependency packages install .la files with libdir='//lib' (conan
        # prefix handling), which libtool chokes on ("not a valid libtool
        # archive").  Rename them away so libtool links the .a directly.
        for dep in self.dependencies.values():
            pf = dep.package_folder
            if not pf:
                self.output.info("skip .la rename for %s (no package_folder)"
                                 % dep.ref.name)
                continue
            for libdir in dep.cpp_info.libdirs:
                if not libdir:
                    continue
                for la in glob.glob(os.path.join(pf, libdir, "*.la")):
                    os.rename(la, la + ".bak")

        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()

        tc = AutotoolsToolchain(self)
        # config.guess does not recognize OHOS (libplist/glue/libtatsu precedent)
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # no Cython/Python bindings on OHOS
        tc.configure_args.append("--without-cython")
        tc.generate()

        env = Environment()
        env.prepend_path("PATH", str(wrapper_dir))
        env.append_path("PKG_CONFIG_PATH", self.generators_folder)
        # configure conftest programs need the conan-cached shared libs
        # (libcurl.so from libtatsu) on the OHOS loader search path.
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                if libdir:
                    env.prepend_path("LD_LIBRARY_PATH", libdir)
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        env.define("CC", compilers.get("c", "clang"))
        env.define("CXX", compilers.get("cpp", "clang++"))
        env.vars(self, scope="build").save_script("hmos_env")

    def build(self):
        apply_conandata_patches(self)
        # E011 family: shipped configure sets umask 077; on HMDFS that makes
        # config.status' temporary awk scripts unreadable -> patch to 022.
        conf = os.path.join(self.source_folder, "configure")
        replace_in_file(self, conf, "umask 077", "umask 022")

        autotools = Autotools(self)
        autotools.configure()
        # R9: single job - parallel make hits HMDFS jobserver fifo EPERM
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING*", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["imobiledevice-1.0"]
        self.cpp_info.set_property("cmake_file_name", "libimobiledevice")
        self.cpp_info.set_property("pkg_config_name", "libimobiledevice-1.0")
        self.cpp_info.requires = [
            "libusbmuxd::libusbmuxd",
            "libplist::libplist",
            "libimobiledevice-glue::libimobiledevice-glue",
            "libtatsu::libtatsu",
            "openssl::openssl",
        ]
