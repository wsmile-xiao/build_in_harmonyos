#!/usr/bin/env python3
"""Conan recipe for libmwaw-tools 0.3.22 — command-line tools for legacy Mac
text documents (MacWrite, ClarisWorks, ...).

Upstream project: libmwaw (SourceForge, LGPL-2.1). Debian/Ubuntu split the
libmwaw source build into libmwaw / libmwaw-dev / libmwaw-doc / libmwaw-tools;
this package adapts the whole source build and ships the command-line tools
(mwaw2csv, mwaw2html, mwaw2raw, mwaw2svg, mwaw2text, mwawFile, mwawZip)
together with the libmwaw shared library they link against.

Build system: Autotools (configure + make)
Dependencies (via pkg-config):
  - librevenge-0.0 / librevenge-generators-0.0 / librevenge-stream-0.0
  - zlib

OHOS adaptation notes (patches/):
  - config.guess: add HarmonyOS system identification
    (2014-vintage script predates HarmonyOS; outputs
    aarch64-unknown-linux-ohos for native builds)
  - config.sub: add linux-ohos triplet to the KERNEL-OS whitelist
  - configure/config.status: umask 077 -> 022 for the config.status temp
    directory (HMDFS ignores umask-077 dirs -> "Permission denied" when
    config.status writes subs1.awk)
  - dependency staging: the librevenge package ships .pc files with a
    hard-coded prefix=/ and .la files whose embedded prefix is stale
    ("//lib/librevenge-0.0.la is not a valid libtool archive"). Both
    artifacts are only valid for a system install, so this recipe stages
    plain .a copies + locally-generated .pc files and points PKG_CONFIG_PATH
    at them. libtool then links raw static archives and never reads .la.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibMwawToolsConan(ConanFile):
    name = "libmwaw-tools"
    version = "0.3.22"
    description = ("Command-line tools to convert legacy Mac text documents "
                   "(MacWrite, ClarisWorks, ...) based on the libmwaw library")
    license = "LGPL-2.1-or-later OR MPL-2.0"
    homepage = "https://sourceforge.net/projects/libmwaw/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # configure.ac: PKG_CHECK_MODULES REVENGE / REVENGE_GENERATORS /
        # REVENGE_STREAM (librevenge package) and ZLIB (zlib package).
        self.requires("librevenge/0.0.5")
        # zlib override: libmwaw-0.3.so is shared and statically absorbs
        # libz.a via the staging dir. The published zlib/1.3.1 binary is
        # non-PIC (configure --static without -fPIC), which fails on aarch64
        # with "relocation R_AARCH64 ... against symbol 'z_errmsg'; recompile
        # with -fPIC" at the CXXLD libmwaw-0.3.la step. zlib/1.3.1.1 is the
        # same-source (-fPIC) static variant; override=True also unifies
        # librevenge's transitive zlib/1.3.1 requirement, avoiding the
        # "Version conflict between zlib/1.3.1.1 and zlib/1.3.1" error
        # (repo precedent: abiword-plugin-docbook).
        self.requires("zlib/1.3.1.1", override=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _staging(self):
        root = os.path.join(self.build_folder, "depstaging")
        return root, os.path.join(root, "lib")

    def _write_pc(self, name, prefix, libs, desc, version, include_subdir=""):
        root, _ = self._staging()
        pc_dir = os.path.join(root, "lib", "pkgconfig")
        pc = (f"prefix={prefix}\n"
              f"exec_prefix=${{prefix}}\n"
              f"libdir=${{prefix}}/lib\n"
              f"includedir=${{prefix}}/include{include_subdir}\n\n"
              f"Name: {name}\nDescription: {desc}\nVersion: {version}\n"
              f"Libs: -L${{libdir}} {libs}\n"
              f"Cflags: -I${{includedir}}\n")
        save(self, os.path.join(pc_dir, f"{name}.pc"), pc)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Upstream builds documentation with doxygen by default; the CI
        # worker has no doxygen and docs are not part of this package.
        tc.configure_args.append("--with-docs=no")
        tc.generate()

        root, dep_lib = self._staging()
        env = Environment()
        # Point pkg-config at locally-generated .pc files (correct prefix)
        # so configure resolves every dependency against the staging dir.
        env.define("PKG_CONFIG_PATH", os.path.join(dep_lib, "pkgconfig"))
        env.define("PKG_CONFIG", "pkg-config")
        envvars = env.vars(self)
        envvars.save_script("conanbuildenv_pkgconfig")

    def build(self):
        apply_conandata_patches(self)
        # Stage plain .a copies + correct-prefix .pc files. The published
        # librevenge .pc/.la files carry prefix=/ (system-install only),
        # which breaks both pkg-config and libtool in the package layout.
        root, dep_lib = self._staging()
        os.makedirs(os.path.join(dep_lib, "pkgconfig"), exist_ok=True)
        rev = self.dependencies["librevenge"]
        zlib = self.dependencies["zlib"]
        for f in os.listdir(os.path.join(rev.package_folder, "lib")):
            if f.startswith("librevenge") and f.endswith(".a"):
                shutil.copy(os.path.join(rev.package_folder, "lib", f), dep_lib)
        shutil.copy(os.path.join(zlib.package_folder, "lib", "libz.a"), dep_lib)
        # Headers
        inc = os.path.join(root, "include")
        os.makedirs(inc, exist_ok=True)
        shutil.copytree(os.path.join(rev.package_folder, "include", "librevenge-0.0"),
                        os.path.join(inc, "librevenge-0.0"))
        for h in ("zlib.h", "zconf.h"):
            shutil.copy(os.path.join(zlib.package_folder, "include", h), inc)
        # .pc files with the real staging prefix
        self._write_pc("zlib", root, "-lz", "zlib compression library", zlib.ref.version)
        # The librevenge headers live in include/librevenge-0.0/{librevenge,
        # librevenge-generators,librevenge-stream} — mirror the published
        # .pc Cflags (-I${includedir}/librevenge-0.0).
        self._write_pc("librevenge-0.0", root, "-lrevenge-0.0",
                       "Librevenge stream library", "0.0.5", "/librevenge-0.0")
        self._write_pc("librevenge-generators-0.0", root,
                       "-lrevenge-generators-0.0 -lrevenge-0.0",
                       "Librevenge generators library", "0.0.5", "/librevenge-0.0")
        self._write_pc("librevenge-stream-0.0", root,
                       "-lrevenge-stream-0.0 -lrevenge-0.0",
                       "Librevenge stream library", "0.0.5", "/librevenge-0.0")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j4"])

    def package(self):
        copy(self, "COPYING.LGPL", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING.MPL", self.source_folder, os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Tools live in bin/; the libmwaw shared library is shipped alongside
        # (its dependencies are linked in statically).
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include/libmwaw-0.3"]
        self.cpp_info.libs = ["mwaw-0.3"]
        self.cpp_info.set_property("cmake_file_name", "libmwaw")
        self.cpp_info.set_property("cmake_target_name", "libmwaw::libmwaw")
