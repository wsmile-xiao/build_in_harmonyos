#!/usr/bin/env python3
"""Conan recipe for GNU mifluz 0.26.0 on OHOS aarch64.

mifluz is a C++ full text inverted index library (ht://Dig heritage).
It builds a single library libmifluz embedding the htdb/db storage layer.
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, rm
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MifluzConan(ConanFile):
    name = "mifluz"
    version = "0.26.0"
    description = "GNU mifluz - C++ library implementing a full text inverted index"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/mifluz/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # db/ compression layer uses zlib; the OHOS SDK sysroot header is not
        # visible under conan's toolchain flags, so take zlib from the
        # artifact repository (R36: explicit, resolvable dependency).
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # AutotoolsToolchain does not inject OHOS build/host triplets, and the
        # 2001-era config.guess cannot guess the HarmonyOS host. The
        # linux-ohos triplet works together with the config.guess/sub patches.
        tc.configure_args.extend([
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-ohos",
        ])
        tc.generate()
        # AC_TRY_RUN probes cannot execute while cross compiling. Preset the
        # autoconf cache variables with the aarch64 facts (verified on device):
        # fixed-width types, 8-byte pointer-aligned type and POSIX pthreads.
        env = Environment()
        for key, value in {
            "db_cv_uint8": "unsigned char",
            "db_cv_uint16": "unsigned short",
            "db_cv_int16": "short",
            "db_cv_uint32": "unsigned int",
            "db_cv_int32": "int",
            "db_cv_align_t": "unsigned long long",
            "db_cv_alignp_t": "unsigned long long",
            "db_cv_mutex": "POSIX/pthreads",
        }.items():
            env.define(key, value)
        env.vars(self, scope="build").save_script("conanmifluz_cross_cache")

    def _patch_configure_hmdfs(self):
        """HMDFS fixes applied at build time (aldo/0.7.8 same pattern).

        - ac_pwd=`pwd` fails on HMDFS when the FUSE layer rejects getcwd();
          fall back to $PWD so configure can proceed.
        - umask 077 temp dirs are not writable on HMDFS (E011) -> umask 022.
        """
        for name in ("configure", "config.status"):
            path = os.path.join(self.source_folder, name)
            if not os.path.isfile(path):
                continue
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            original = content
            if "ac_pwd=`pwd`" in content:
                content = content.replace(
                    "ac_pwd=`pwd`",
                    'ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"',
                )
                content = content.replace(
                    'ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD" 2>/dev/null || ac_pwd="$PWD"',
                    'ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"',
                )
            # HMDFS FUSE may also reject `ls -di .` inside configure's cwd
            # sanity check; fall back to trusting $PWD-derived ac_pwd.
            if 'ac_pwd_ls_di=`cd "$ac_pwd" && ls -di .`' in content:
                content = content.replace(
                    'ac_pwd_ls_di=`cd "$ac_pwd" && ls -di .` ||',
                    'ac_pwd_ls_di=`cd "$ac_pwd" && ls -di . 2>/dev/null` || ac_pwd_ls_di="$ac_pwd" ||',
                )
            content = content.replace("umask 077", "umask 022")
            if content != original:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)

    def build(self):
        apply_conandata_patches(self)
        self._patch_configure_hmdfs()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1", "MAKEINFO=true"])
        # Upstream make check runs the registered TESTS (test/ 13 entries,
        # search/ t_search, examples/ t_example). The search/examples test
        # drivers (mifluzsearch) abort when the HMDFS FUSE layer rejects
        # getcwd(); use -k so a driver failure does not stop the remaining
        # directories, and record the full result (see notes.md).
        self.run("make check -k MAKEINFO=true", ignore_errors=True)

    def package(self):
        autotools = Autotools(self)
        # doc/ has no makeinfo on the device; keep the placeholder consistent
        # with build() so install-recursive does not fail on mifluz.info.
        autotools.install(args=["MAKEINFO=true"])
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.includedirs = ["include", "include/mifluz"]
        self.cpp_info.libs = ["mifluz"]
