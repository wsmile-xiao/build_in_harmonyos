#!/usr/bin/env python3
"""Conan recipe for minizip 1.3.1 (part of zlib).

minizip is a contrib component of zlib, located in contrib/minizip/.
Build process:
  1. Build zlib (static) from the top-level source
  2. Compile minizip library sources directly (avoids autotools configure
     issues on HMDFS — E114 mktemp + cat broken pipe)
  3. Create shared + static library and install
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches


class MinizipConan(ConanFile):
    name = "minizip"
    version = "1.3.1"
    description = "Zip library from zlib"
    license = "Zlib"
    homepage = "https://github.com/madler/zlib"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        pass

    def layout(self):
        self.folders.build = "build"
        self.folders.source = "source"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder

        # ── 1. Build zlib (static) ──
        with open(os.path.join(src, "configure.log"), "w") as _log:
            pass  # touch
        self.run("cd {} && ./configure --static --prefix={}".format(src, self.package_folder))
        self.run("cd {} && make -j$(nproc)".format(src))
        self.run("cd {} && make install".format(src))

        # ── 2. Build minizip library (direct compilation) ──
        minizip_src = os.path.join(src, "contrib", "minizip")
        build_dir = os.path.join(src, "minizip-build")
        os.makedirs(build_dir, exist_ok=True)

        # minizip library source files
        minizip_sources = ["ioapi.c", "mztools.c", "unzip.c", "zip.c"]
        # minizip command-line tool sources
        tool_sources = {"miniunz.c": "miniunzip", "minizip.c": "minizip"}

        cflags = "-fPIC -O2 -I{} -I{}".format(src, minizip_src)
        ldflags = "-L{}/lib".format(self.package_folder)

        # Compile library objects
        obj_files = []
        for srcfile in minizip_sources:
            objfile = os.path.join(build_dir, srcfile.replace(".c", ".o"))
            self.run("clang {} -c {}/{} -o {}".format(
                cflags, minizip_src, srcfile, objfile))
            obj_files.append(objfile)

        # Create shared library
        shared_lib = os.path.join(build_dir, "libminizip.so.1.0.0")
        obj_list = " ".join(obj_files)
        self.run("clang -shared -Wl,-soname,libminizip.so.1 -o {} {} {} -lz".format(
            shared_lib, obj_list, ldflags))
        # Create symlinks
        self.run("cd {} && ln -sf libminizip.so.1.0.0 libminizip.so.1 && ln -sf libminizip.so.1.0.0 libminizip.so".format(build_dir))

        # Create static library
        static_lib = os.path.join(build_dir, "libminizip.a")
        self.run("llvm-ar cr {} {}".format(static_lib, obj_list))
        self.run("llvm-ranlib {}".format(static_lib))

        # Compile and link command-line tools
        for srcfile, toolname in tool_sources.items():
            objfile = os.path.join(build_dir, srcfile.replace(".c", ".o"))
            self.run("clang {} -c {}/{} -o {}".format(
                cflags, minizip_src, srcfile, objfile))
            self.run("clang -o {}/{} {} {}/libminizip.so -lz {} -Wl,-rpath,{}/lib".format(
                build_dir, toolname, objfile, build_dir, ldflags, self.package_folder))

        # Store build artifacts for package()
        self._build_dir = build_dir
        self._minizip_src = minizip_src

    def package(self):
        build_dir = getattr(self, "_build_dir", os.path.join(self.source_folder, "minizip-build"))
        minizip_src = getattr(self, "_minizip_src", os.path.join(self.source_folder, "contrib", "minizip"))

        # Install minizip library
        libdir = os.path.join(self.package_folder, "lib")
        os.makedirs(libdir, exist_ok=True)
        copy(self, "libminizip.so*", build_dir, libdir)
        copy(self, "libminizip.a", build_dir, libdir)

        # Install minizip headers
        incdir = os.path.join(self.package_folder, "include", "minizip")
        os.makedirs(incdir, exist_ok=True)
        for h in ["crypt.h", "ioapi.h", "mztools.h", "unzip.h", "zip.h"]:
            src_h = os.path.join(minizip_src, h)
            if os.path.exists(src_h):
                shutil.copy2(src_h, os.path.join(incdir, h))

        # Install command-line tools
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        copy(self, "miniunzip", build_dir, bindir)
        copy(self, "minizip", build_dir, bindir)

        # Install pkg-config file
        pkgdir = os.path.join(libdir, "pkgconfig")
        os.makedirs(pkgdir, exist_ok=True)
        pc_content = """prefix=${pcfiledir}/../..
exec_prefix=${prefix}
libdir=${exec_prefix}/lib
includedir=${prefix}/include

Name: minizip
Description: Zip library from zlib
Version: 1.3.1
Requires: zlib
Libs: -L${libdir} -lminizip
Cflags: -I${includedir}
"""
        with open(os.path.join(pkgdir, "minizip.pc"), "w") as f:
            f.write(pc_content)

        # Install man pages
        mandir = os.path.join(self.package_folder, "share", "man", "man1")
        os.makedirs(mandir, exist_ok=True)
        for m in ["miniunzip.1", "minizip.1"]:
            src_m = os.path.join(minizip_src, m)
            if os.path.exists(src_m):
                shutil.copy2(src_m, os.path.join(mandir, m))

        # Clean up zlib artifacts (zlib is a separate package)
        zlib_lib = os.path.join(self.package_folder, "lib", "libz.a")
        if os.path.exists(zlib_lib):
            os.remove(zlib_lib)
        for h in ["zlib.h", "zconf.h"]:
            p = os.path.join(self.package_folder, "include", h)
            if os.path.exists(p):
                os.remove(p)
        zlib_pc = os.path.join(pkgdir, "zlib.pc")
        if os.path.exists(zlib_pc):
            os.remove(zlib_pc)
        zlib_man = os.path.join(self.package_folder, "share", "man", "man3", "zlib.3")
        if os.path.exists(zlib_man):
            os.remove(zlib_man)

    def package_info(self):
        self.cpp_info.libs = ["minizip"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["z"]
