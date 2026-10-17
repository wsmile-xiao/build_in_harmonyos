#!/usr/bin/env python3
"""Conan recipe — libpar2 0.4 (Autotools, C++)

libpar2 is the PAR 2.0 parity-archive library extracted from par2cmdline 0.4.
It depends on libsigc++ 2.x (sigc++-2.0 pkg-config module, published on ohpcd
as libsigc/2.10.8).

OHOS adaptations:
  - config.sub patched to canonicalize aarch64-*-linux-ohos (patch 0001).
  - AC_CHECK_LIB(stdc++) probe bypassed via the autoconf cache variable
    `ac_cv_lib_stdcpp_main=yes`; configure's success branch that appends
    -lstdc++ to LIBS is removed by patch 0002 (OHOS links libc++ only).
  - 2003-era code forced to C++11 (-std=c++11, same as nixpkgs clang path).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps, PkgConfigDeps
from conan.tools.layout import basic_layout


class Libpar2Conan(ConanFile):
    name = "libpar2"
    version = "0.4"
    description = "Library for using PAR2 parity archive volume sets (verification and repair)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/Parchive/libpar2"
    url = ""
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("libsigc/2.10.8")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libpar2 supports Linux/OHOS only")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # AutotoolsDeps feeds -I/-L/-l from libsigc into configure/make.
        AutotoolsDeps(self).generate()
        # configure.ac uses PKG_CHECK_MODULES(SIGC, sigc++-2.0); libsigc's
        # package_info declares pkg_config_name=sigc++-2.0, so PkgConfigDeps
        # emits sigc++-2.0.pc into the generators folder. PKG_CONFIG_PATH is
        # injected below so the probe succeeds.
        PkgConfigDeps(self).generate()

        tc = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            # AutotoolsToolchain does not inject OHOS triplets; config.sub is
            # patched (0001) to accept aarch64-*-linux-ohos.
            tc.configure_args.extend([
                "--build=aarch64-linux-ohos",
                "--host=aarch64-linux-ohos",
            ])
        # Bypass the AC_CHECK_LIB(stdc++) link probe. Note the cache variable
        # name is ac_cv_lib_stdcpp_main (autoconf maps '+' to 'p'), NOT
        # ac_cv_lib_stdcpp__main as sometimes written. configure's success
        # branch would still add -lstdc++ to LIBS; patch 0002 removes it.
        tc.configure_args.append("ac_cv_lib_stdcpp_main=yes")
        # PkgConfigDeps .pc files live in the generators folder; configure's
        # PKG_CHECK_MODULES needs PKG_CONFIG_PATH pointing there.
        tc.configure_args.append("PKG_CONFIG_PATH={}".format(self.generators_folder))
        # 2003-era code: keep C++11 (profile defaults to cppstd=17).
        tc.cxxflags.append("-std=c++11")
        tc.generate()

        # configure conftests link against the shared libsigc and then RUN the
        # produced binaries; the OHOS loader has no default search path for
        # conan-cached shared libs, so point LD_LIBRARY_PATH at dep libdirs.
        env = Environment()
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.vars(self, scope="build").save_script("conanbuild_runpath")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # R9: single job — parallel make hits HMDFS jobserver fifo EPERM.
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Remove libtool *.la wrappers manually (Conan 2 copy() has no delete=).
        import glob as _glob
        for _la in _glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(_la)
        # Upstream Makefile.in ships `library_include_HEADERS = *.h` as a
        # literal wildcard, so `make install` never expands it and no header
        # lands in include/libpar2/. Copy the headers explicitly.
        copy(self, "*.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include", "libpar2"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["par2"]
        self.cpp_info.includedirs = [
            os.path.join("include", "libpar2"),
            os.path.join("lib", "libpar2", "include"),
        ]
