#!/usr/bin/env python3
"""Conan recipe for libmwaw 0.3.23 — library for legacy Mac text documents.

libmwaw parses MacWrite, ClarisWorks, TeachTxt, WriteNow and other classic
Mac word processor formats on top of librevenge streams. This package ships
the library and its headers; the command-line conversion tools are adapted
separately as libmwaw-tools/0.3.22 (same upstream source tree, one release
older). The tools are disabled here (--disable-tools) because this package
has no consumer for them.

Build system: Autotools (configure + make)
Dependencies (via pkg-config):
  - librevenge-0.0 / librevenge-generators-0.0 / librevenge-stream-0.0
  - zlib

OHOS adaptation notes (patches/):
  - config.guess: the bundled 2024 script has no HarmonyOS branch (`uname -s`
    reports "HarmonyOS"); added a leading branch reporting the linux-ohos
    triplet. The bundled 2024 config.sub accepts linux-ohos* natively, so
    this release needs no config.sub patch (0.3.22 did for its 2014 copy).
  - configure/config.status: umask 077 -> 022 (HMDFS ignores umask-077 dirs
    -> "Permission denied" when config.status writes subs1.awk).
  - dependency staging: the librevenge package ships .pc files with a
    hard-coded prefix=/ and .la files whose embedded prefix is stale; this
    recipe stages plain .a copies + locally-generated .pc files and points
    PKG_CONFIG_PATH at them (same approach as libmwaw-tools/0.3.22).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibMwawConan(ConanFile):
    name = "libmwaw"
    version = "0.3.23"
    description = ("Import library for classic Mac text document formats "
                   "(MacWrite, ClarisWorks, ...) based on librevenge")
    license = "LGPL-2.1-or-later OR MPL-2.0"
    homepage = "https://sourceforge.net/projects/libmwaw/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # configure.ac: PKG_CHECK_MODULES REVENGE / REVENGE_GENERATORS /
        # REVENGE_STREAM (librevenge package) and ZLIB (zlib package).
        self.requires("librevenge/0.0.5")
        # zlib is a direct requirement (the staged libz.a symbols are
        # referenced by libmwaw, and cpp_info.requires may only name direct
        # requirements). force=True keeps that direct edge while replacing
        # librevenge's transitive zlib/1.3.1 — the same-source -fPIC variant
        # is required because the shared libmwaw-0.3 statically absorbs the
        # staged libz.a and the published non-PIC zlib/1.3.1 fails on aarch64
        # with "relocation R_AARCH64 ... recompile with -fPIC" (repo
        # precedent: libmwaw-tools/0.3.22, abiword-plugin-docbook).
        self.requires("zlib/1.3.1.1", force=True)

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
        # Docs need doxygen, which the CI worker does not have; the conversion
        # tools are packaged separately as libmwaw-tools.
        tc.configure_args.append("--with-docs=no")
        tc.configure_args.append("--disable-tools")
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        else:
            tc.configure_args.append("--disable-static")
            tc.configure_args.append("--enable-shared")
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
        # src/tools (mwawFile/mwawZip) builds unconditionally in 0.3.23 —
        # --disable-tools only gates the src/conv converters — but those
        # helpers are not part of the library deliverable: they ship in
        # libmwaw-tools. Drop the installed bin/ from this package.
        tools_dir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(tools_dir):
            shutil.rmtree(tools_dir)
        # libtool .la files embed absolute paths of the (per-run randomly
        # named) build/staging prefixes and go stale once the package moves —
        # the very breakage the librevenge .la files cause downstream. Conan
        # consumers use CMakeDeps/pkg-config metadata, so drop them.
        lib_dir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(lib_dir):
            for f in os.listdir(lib_dir):
                if f.endswith(".la"):
                    os.unlink(os.path.join(lib_dir, f))
            # The installed .pc embeds the per-run randomly named build/staging
            # prefix (same churn as the .la files); consumers use cpp_info /
            # CMakeDeps metadata, so the pkgconfig dir is dead weight.
            shutil.rmtree(os.path.join(lib_dir, "pkgconfig"), ignore_errors=True)

    def package_info(self):
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include/libmwaw-0.3"]
        self.cpp_info.libs = ["mwaw-0.3"]
        # The static libmwaw references zlib/librevenge symbols; forward the
        # dependency so consumers (CMakeDeps) link them in the right order.
        self.cpp_info.requires = ["librevenge::librevenge", "zlib::zlib"]
        self.cpp_info.set_property("cmake_file_name", "libmwaw")
        self.cpp_info.set_property("cmake_target_name", "libmwaw::libmwaw")
