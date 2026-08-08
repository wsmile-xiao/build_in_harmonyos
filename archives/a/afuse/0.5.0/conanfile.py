#!/usr/bin/env python3
"""Conan recipe for afuse 0.5.0 — Autotools (configure + make).

afuse is a user-space automounter implemented using FUSE.
It builds a single daemon executable (`afuse`) plus a helper shell
script (`afuse-avahissh`).

HarmonyOS adaptation (see patches):
  - Upstream configure required the FUSE 2.x pkg-config module `fuse`
    (`fuse >= 2.3`) and FUSE_USE_VERSION=25.  The artifact repo only
    ships libfuse 3.x, so configure.ac was switched to the `fuse3`
    module and FUSE_USE_VERSION=31, and afuse.c was ported to the
    FUSE 3.x high-level API (fuse_main signature, fuse_operations
    callback signatures, fuse_fill_dir_t flags, utime -> utimens,
    dropped ftruncate/fgetattr members).

License: GPL-2.0
"""
import os
import glob

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class AfuseConan(ConanFile):
    name = "afuse"
    version = "0.5.0"
    description = "afuse - an automounter implemented with FUSE (userspace)"
    license = "GPL-2.0"
    homepage = "https://github.com/pcarrier/afuse"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # afuse needs libfuse 3.x for the FUSE high-level API
        self.requires("libfuse/3.18.2")

    def build_requirements(self):
        # GitHub tag archive 不含预生成 configure（autoreconf 产物不进版本库），
        # 构建时须 autoreconf 自举；CI Worker 缺 automake/aclocal（E178），
        # 通过 tool_requires 用 build profile 解析（同 duo-unix 配方做法）。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: use in ("Linux", "OHOS") format
        if self.settings.os not in ("Linux", "FreeBSD", "OHOS"):
            raise ConanInvalidConfiguration(
                f"afuse supports only Linux, FreeBSD and OHOS, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Make libfuse's fuse3.pc visible to configure's PKG_CHECK_MODULES
        PkgConfigDeps(self).generate()

        tc = AutotoolsToolchain(self)
        # Avoid running anything at configure time that needs the FUSE
        # device; runtime mounting is a platform concern, not build.
        #
        # pkg.m4 (PKG_CHECK_MODULES) lives under the hnp pkg-config install.
        # autoconf's aclocal must find it when we bootstrap configure.ac.
        # NOTE: inject via the toolchain environment (-> conanautotoolstoolchain.sh,
        # sourced by conanbuild.sh during self.run()) — recipe's own buildenv_info
        # is NOT applied to its own build env.
        env = tc.environment()
        for _d in sorted(glob.glob("/data/service/hnp/*/*/share/aclocal")):
            env.append_path("ACLOCAL_PATH", _d)
        tc.generate(env=env)

    def build(self):
        os.umask(0)
        apply_conandata_patches(self)

        # GitHub tag archive: no pre-generated configure — bootstrap it.
        self.run("autoreconf --install --verbose", cwd=self.source_folder)

        # OHOS/HMDFS: config.status creates its temp dir with `umask 077`,
        # yielding mode drwx--S--- which the sandbox cannot write into.
        # Relax to 000 so the generated temp dir is writable (E114).
        self.run("sed -i 's/umask 077/umask 000/g' configure", cwd=self.source_folder)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # afuse is a command-line tool: expose bin/, no libraries
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "dl"]
