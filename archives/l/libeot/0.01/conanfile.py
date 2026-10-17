#!/usr/bin/env python3
"""Conan recipe for libeot 0.01 — direct C99 compilation of the upstream sources.

Upstream ships autotools sources (configure.ac + Makefile.am) without generated
configure scripts. Bootstrapping them needs automake and libtoolize, neither of
which is present in the reviewed build profile PATH (the hnp toolchain ships
autoconf 2.72, m4 and perl but no automake/libtool), so this recipe compiles
the exact upstream source list from the v0.01 Makefile.am with upstream's own
flags: release = "-O2 --std=c99 -DDECOMPRESS_ON".

Upstream builds a shared-only libtool library (LT_INIT [disable-static]); the
static default here follows the archive convention, with a shared option.
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save


# libeot_la_SOURCES from the upstream Makefile.am (v0.01 tag), .c files only.
SOURCES = [
    "src/libeot.c",
    "src/EOT.c",
    "src/writeFontFile.c",
    "src/triplet_encodings.c",
    "src/util/stream.c",
    "src/ctf/parseCTF.c",
    "src/ctf/parseTTF.c",
    "src/ctf/SFNTContainer.c",
    "src/lzcomp/ahuff.c",
    "src/lzcomp/bitio.c",
    "src/lzcomp/liblzcomp.c",
    "src/lzcomp/lzcomp.c",
    "src/lzcomp/mtxmem.c",
]

PKGCONFIG_TEMPLATE = """prefix={prefix}
exec_prefix={prefix}
libdir=${{prefix}}/lib
includedir=${{prefix}}/include

Name: libeot
Description: Library for parsing Embedded OpenType files and converting them to other formats
Version: 0.01
Libs: -L${{libdir}} -leot
Cflags: -I${{includedir}}
"""


class LibeotConan(ConanFile):
    name = "libeot"
    version = "0.01"
    description = "Library for parsing Microsoft Embedded OpenType (EOT) fonts and converting them to TrueType"
    license = "MPL-2.0"
    homepage = "https://github.com/umanwizard/libeot"
    url = "https://github.com/umanwizard/libeot"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def layout(self):
        self.folders.source = "."
        self.folders.build = "build"
        self.folders.generators = "build/generators"

    def export_sources(self):
        # No patches: conandata.yml declares none, so this is a no-op kept for
        # the standard recipe structure.
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # The reviewed profile defines tools.build:compiler_executables with the
        # OHOS clang; read it via conf (conan.tools.build lacks the helper on
        # the shipped 2.29.1 build).
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c")
        if not cc:
            raise ConanException(
                "tools.build:compiler_executables must define the C compiler "
                "(see ci/conan/profiles/ohos-aarch64)")
        # The reviewed profile ships binutils (ar, llvm-ar) next to the compiler.
        ar = compilers.get("ar") or os.path.join(os.path.dirname(cc), "ar")

        src = self.source_folder
        bld = self.build_folder
        # Upstream Makefile.am: release_flags = -O2, common_flags = --std=c99 -DDECOMPRESS_ON
        optimization = "-O2" if self.settings.build_type == "Release" else "-g -O0"
        pic = "-fPIC" if (self.options.shared or self.options.fPIC) else ""
        flags = "%s %s --std=c99 -DDECOMPRESS_ON" % (optimization, pic)
        includes = "-I%s -I%s" % (shlex.quote(os.path.join(src, "inc")),
                                  shlex.quote(os.path.join(src, "src")))

        objs = []
        for i, name in enumerate(SOURCES):
            obj = os.path.join(bld, "libeot_%02d.o" % i)
            self.run("%s %s %s -c %s -o %s" % (
                shlex.quote(cc), flags, includes,
                shlex.quote(os.path.join(src, name)), shlex.quote(obj)))
            objs.append(obj)

        if self.options.shared:
            self.run("%s -shared %s -o %s" % (
                shlex.quote(cc), " ".join(shlex.quote(o) for o in objs),
                shlex.quote(os.path.join(bld, "libeot.so"))))
        else:
            self.run("%s rcs %s %s" % (
                shlex.quote(ar),
                shlex.quote(os.path.join(bld, "libeot.a")),
                " ".join(shlex.quote(o) for o in objs)))

        # eot2ttf command-line tool; linked from the objects directly so it
        # works in both static and shared configurations.
        tool_obj = os.path.join(bld, "eot2ttf_main.o")
        self.run("%s %s -I%s -c %s -o %s" % (
            shlex.quote(cc), flags, shlex.quote(os.path.join(src, "inc")),
            shlex.quote(os.path.join(src, "src", "eot2ttf.c")),
            shlex.quote(tool_obj)))
        self.run("%s %s -o %s" % (
            shlex.quote(cc),
            " ".join(shlex.quote(o) for o in objs + [tool_obj]),
            shlex.quote(os.path.join(bld, "eot2ttf"))))

    def package(self):
        src = self.source_folder
        copy(self, "LICENSE", src, os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "*.h", os.path.join(src, "inc"),
             os.path.join(self.package_folder, "include"), keep_path=True)
        copy(self, "*.a", self.build_folder, os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.so", self.build_folder, os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "eot2ttf", self.build_folder, os.path.join(self.package_folder, "bin"), keep_path=False)
        # Generated from the upstream libeot.pc.in template.
        save(self, os.path.join(self.package_folder, "lib", "pkgconfig", "libeot.pc"),
             PKGCONFIG_TEMPLATE.format(prefix=self.package_folder))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libeot")
        self.cpp_info.set_property("cmake_target_name", "libeot")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = ["eot"]
        # The packaged eot2ttf command-line tool (declared in commands.json).
        self.cpp_info.bindirs = ["bin"]
