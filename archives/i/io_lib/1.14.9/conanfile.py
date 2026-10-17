#!/usr/bin/env python3
"""Conan recipe for io_lib 1.14.9 (Staden io_lib) on HarmonyOS PC.

io_lib (libstaden-read) is the C library for reading/writing DNA
sequencing formats (SAM/CRAM/SRF/SCF/ZTR).  Required by srf/0.1
(SRF format C++ implementation, R36 dependency chain).

OHOS-specific adaptations:
  - 2012-era config.guess/config.sub do not know aarch64-linux-ohos:
    replaced with the repository's 2026 versions (patch 0001)
  - curl/zlib/bz2/lzma optional deps: enabled via conan requires and
    injected through a private prefix (R49: never /usr/local)
  - libtool -no-undefined / shared: plain autotools shared build
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class IoLibConan(ConanFile):
    name = "io_lib"
    version = "1.14.9"
    description = (
        "Staden io_lib (libstaden-read): C library for reading and "
        "writing DNA sequencing data formats (SAM/CRAM/SRF/SCF/ZTR)"
    )
    license = "BSD-3-Clause"
    homepage = "https://sourceforge.net/projects/staden/"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def requirements(self):
        # zlib: mandatory in practice (configure ZLIB_CHECK_CONFIG, gzip
        # CRAM paths); curl/bz2/lzma: optional feature deps
        self.requires("zlib/1.3.1.1")
        self.requires("libcurl/8.5.0")
        self.requires("bzip2/1.0.8")
        self.requires("xz/5.8.3.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # OHOS triplet: 2012 config.sub does not know it, patch 0001
        # updates config.guess/sub (build_systems.md §3.1 pattern).
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        # R49: private prefix under build_folder — never shared /usr/local
        prefix = os.path.join(self.build_folder, "prefix")
        tc.configure_args.append(f"--prefix={prefix}")
        # srf needs the ZTR/SRF APIs; shared lib keeps consumers simple
        if not self.options.shared:
            tc.configure_args.append("--disable-shared")
            tc.configure_args.append("--enable-static")

        # R49 / E524: CPPFLAGS/LDFLAGS point at dependency package folders
        # (private per-build paths, never a shared /usr/local)
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.append("CPPFLAGS", f"-I{dep.package_folder}/include")
                env.append("LDFLAGS", f"-L{dep.package_folder}/lib")
        env.append("LDFLAGS",
                   f"-L{os.path.join(self.build_folder, 'prefix', 'lib')}")
        env.vars(self).save_script("io_lib_deps_env")

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        # NOTE: do NOT use autotools.install() — it forces
        # DESTDIR=package_folder, and since --prefix is an absolute path
        # the artifacts would nest under
        # package_folder/<abs-prefix>/lib/... . Plain `make install`
        # lands in the private prefix (build_folder/prefix), which we
        # then copy into the package folder (R49 layout).
        autotools = Autotools(self)
        autotools.make(target="install")
        src_prefix = os.path.join(self.build_folder, "prefix")
        copy(self, "*", src_prefix, self.package_folder)

    def package_id(self):
        del self.info.settings.compiler
        del self.info.settings.build_type

    def package_info(self):
        self.cpp_info.libs = ["staden-read"]
        # upstream installs headers into <prefix>/include/io_lib/ but the
        # headers cross-include as "io_lib/Read.h" — both dirs must be on
        # the include path (mirrors upstream io_lib-config --cflags)
        self.cpp_info.includedirs = ["include", "include/io_lib"]
