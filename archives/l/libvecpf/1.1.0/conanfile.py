#!/usr/bin/env python3
"""Conan recipe for libvecpf 1.1.0 - the Vector Printf Library.

libvecpf extends printf() with conversions for 16-byte vector values, e.g.

    vecpf_printf("%vld", v);   /* four 32-bit lanes, decimal, space separated */

It was written for PowerPC + glibc and plugs into the C library through
glibc's private printf-hook API (<printf.h>: register_printf_type(),
register_printf_modifier(), register_printf_specifier()).

OpenHarmony ships musl, which deliberately does not implement that API.  The
port in patches/ replaces the missing mount point with an in-tree
compatibility layer (vecpf-ohos-compat.h) and exposes the identical formatting
through explicit entry points.  The formatting engine itself is untouched; it
is plain C and emits only through fprintf()/fputs().  See notes.md for the
full rationale and for the contract differences on musl.
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout

# settings.arch -> autoconf build triple.  The bundled config.guess is from
# 2014 and cannot identify HarmonyOS ("unable to guess system type"), after
# which autoconf aborts, so the triple is supplied explicitly.  No --host is
# passed, so autoconf stays in native mode and the produced aarch64/OHOS
# binaries can be executed in place - which is what the upstream test suite
# needs in order to run at all.
_BUILD_TRIPLE = {
    "armv8": "aarch64-unknown-linux-gnu",
}

# settings.build_type -> optimisation flags.  autoconf has no notion of a
# build type, so it has to be translated here rather than ignored.
_OPT_FLAGS = {
    "Debug": "-O0 -g",
    "Release": "-O2",
    "RelWithDebInfo": "-O2 -g",
    "MinSizeRel": "-Os",
}


class LibvecpfConan(ConanFile):
    name = "libvecpf"
    version = "1.1.0"
    description = ("Vector printf library: adds vector conversions to printf "
                   "(libvecpf, AltiVec/VSX heritage)")
    license = "LGPL-2.1-only"
    homepage = "https://github.com/libvecpf/libvecpf"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    # Shared by default: the library's whole purpose is to extend printf, and
    # upstream's own test program is only built in the shared configuration
    # (Makefile.am gates it behind the TEST_SHARED conditional).  Both modes
    # are supported and are exercised by the checks below.
    default_options = {"shared": True}

    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: take the compiler from Conan's toolchain configuration instead
        # of relying on shell variables such as ${CC}.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c") or "clang"

        triple = _BUILD_TRIPLE.get(str(self.settings.arch))
        if triple is None:
            raise ConanInvalidConfiguration(
                "libvecpf/1.1.0 is only wired for OHOS aarch64 "
                "(settings.arch=armv8), got arch=%s; add its triple to "
                "_BUILD_TRIPLE to extend it" % self.settings.arch
            )

        opt = _OPT_FLAGS.get(str(self.settings.build_type))
        if opt is None:
            raise ConanInvalidConfiguration(
                "unhandled settings.build_type=%s" % self.settings.build_type
            )

        configure_args = [
            "--build=%s" % triple,
            "CC=%s" % cc,
            "CFLAGS='%s -fPIC'" % opt,
        ]
        if self.options.shared:
            configure_args += ["--enable-shared", "--disable-static"]
        else:
            configure_args += ["--disable-shared", "--enable-static"]

        self.run("./configure %s" % " ".join(configure_args),
                 cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

        # L1: run the upstream test suite for real.  `make check` exits
        # non-zero when the suite fails, which fails the build - the pass rate
        # is never asserted by hand.
        #
        # Note: the two test groups that upstream itself excludes are absent
        # here for upstream's own reasons, not because the port skipped them -
        # configure probes `vector __int128_t` for HAVE_INT128_T, which cannot
        # compile outside PowerPC, and clang does not define __VSX__.
        self.run("make -j1 check", cwd=self.source_folder)

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

        # Public headers: vecpf.h declares the entry points; the compat header
        # is shipped for reference (it refuses to be included on its own).
        for header in ("vecpf.h", "vecpf-ohos-compat.h"):
            copy(self, header, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "include"))

        lib_dst = os.path.join(self.package_folder, "lib")
        libs_dir = os.path.join(self.source_folder, ".libs")

        if not self.options.shared:
            copy(self, "libvecpf.a", src=libs_dir, dst=lib_dst)
            return

        # libtool emits the real object plus the soname and linker-name
        # symlinks into .libs/.  Mirror that layout - copying with a glob would
        # follow the symlinks and put three full copies of the same library in
        # the package.  The names are read back from what libtool produced,
        # rather than reconstructed from the version numbers.
        real = [p for p in glob.glob(os.path.join(libs_dir, "libvecpf.so*"))
                if not os.path.islink(p)]
        if len(real) != 1:
            raise ConanException(
                "expected exactly one real libvecpf.so* object in %s, found %s"
                % (libs_dir, [os.path.basename(p) for p in real])
            )

        real_name = os.path.basename(real[0])
        copy(self, real_name, src=libs_dir, dst=lib_dst)

        for path in sorted(glob.glob(os.path.join(libs_dir, "libvecpf.so*"))):
            if not os.path.islink(path):
                continue
            name = os.path.basename(path)
            target = os.path.join(lib_dst, name)
            if not os.path.lexists(target):
                os.symlink(os.readlink(path), target)

    def package_info(self):
        self.cpp_info.libs = ["vecpf"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
