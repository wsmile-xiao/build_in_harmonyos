#!/usr/bin/env python3
"""Conan recipe for xapian 2.0.0 (HarmonyOS/OHOS aarch64 port)."""

import os
import shutil

from conan import ConanFile
from conan.tools.build import load_toolchain_args
from conan.tools.files import (
    apply_conandata_patches,
    collect_libs,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class XapianConan(ConanFile):
    name = "xapian"
    version = "2.0.0"
    description = ("Search engine library with probabilistic information "
                   "retrieval APIs")
    license = "GPL-2.0-or-later"
    homepage = "https://xapian.org/"
    url = "https://xapian.org/"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # glass/honey backends need zlib (configure aborts without zlib.h).
        self.requires("zlib/1.3.1.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()

        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-documentation")
        tc.configure_args.append("--disable-dependency-tracking")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # basic_layout keeps the downloaded source in source_folder and works
        # from a copied tree next to build_folder. Conan applies conandata
        # patches to that build copy, so configure must come from the patched
        # copy as well (not the pristine source tree).
        configure_source = self.source_folder
        if self.settings.os == "OHOS":
            patched_source = os.path.dirname(self.build_folder)
            if os.path.isfile(os.path.join(patched_source, "configure")):
                configure_source = patched_source
        configure = os.path.join(configure_source, "configure")
        if os.path.isfile(configure):
            os.chmod(configure, 0o755)
        autotools = Autotools(self)
        configure_args = self._load_configure_args()
        if self.settings.os == "OHOS":
            # bash cannot resolve HMDFS working directories on this device,
            # while the system POSIX shell can. The configured compiler wrappers
            # still need to be invoked through a shell, and the SDK uses LLVM
            # binutils names.
            config_shell = "/system/bin/sh"
            cc = shutil.which("clang") or "clang"
            cxx = shutil.which("clang++") or "clang++"
            ar = shutil.which("llvm-ar") or shutil.which("ar") or "ar"
            ranlib = shutil.which("llvm-ranlib") or shutil.which("ranlib") or "ranlib"
            nm = shutil.which("llvm-nm") or shutil.which("nm") or "nm"
            ld = shutil.which("ld.lld") or shutil.which("ld") or "ld"
            self.run(
                f'CC="{config_shell} {cc}" CXX="{config_shell} {cxx}" '
                f'AR="{ar}" RANLIB="{ranlib}" NM="{nm}" LD="{ld}" '
                f'CONFIG_SHELL="{config_shell}" '
                f'"{config_shell}" "{configure}" {configure_args}'
            )
        else:
            config_shell = shutil.which("bash") or "sh"
            self.run(
                f'CONFIG_SHELL="{config_shell}" '
                f'"{config_shell}" "{configure}" {configure_args}'
            )
        autotools.make()

    def _load_configure_args(self):
        return load_toolchain_args(self.generators_folder).get("configure_args")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

        config = os.path.join(self.package_folder, "bin", "xapian-config")
        if os.path.isfile(config):
            os.chmod(config, 0o755)

    def package_info(self):
        self.cpp_info.libs = collect_libs(self) or ["xapian"]
        # Upstream installs the CLI utilities (xapian-delve, xapian-compact,
        # xapian-check, ...) into bin/ alongside the library.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "xapian")
        self.cpp_info.set_property("cmake_target_name", "xapian::xapian")
        # The package is named xapian in Conan, while upstream keeps the
        # xapian-core pkg-config module name.
        self.cpp_info.set_property("pkg_config_name", "xapian-core")
        self.cpp_info.requires = ["zlib::zlib"]
        # Ship the command line utilities (xapian-delve, xapian-compact, ...)
        # on PATH for consumers that use this package as a tool provider.
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
