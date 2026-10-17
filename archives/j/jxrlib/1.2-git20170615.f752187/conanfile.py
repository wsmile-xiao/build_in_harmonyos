#!/usr/bin/env python3
"""Conan recipe — jxrlib 1.2-git20170615.f752187 (upstream raw Makefile).

libjpegxr (JPEG XR codec) + libjxrglue (container/glue + BMP/TIF/PNM I/O),
plus the JxrDecApp/JxrEncApp command line tools. Upstream builds through a
hand-written Makefile with hard-coded cc/ar/ranlib, fixed CFLAGS and
LDFLAGS-less link rules, so patch 0001 routes the Conan toolchain in
(CC ?= /AR ?= /RANLIB ?=, EXTRA_CFLAGS/EXTRA_LDFLAGS appended), declares
_byteswap_ulong for toolchains that reject implicit declarations, adds the
missing <stdlib.h>/<wchar.h> includes, and adds a headless --version probe
to both tools (darkhttpd/divxcomp precedent) for the L2 smoke check.

Upstream ships no test suite (audit in test_package/MANIFEST.yml);
verification is the test_package consumer driving a real PK* API
encode->decode roundtrip against the packaged libraries.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class JxrlibConan(ConanFile):
    name = "jxrlib"
    version = "1.2-git20170615.f752187"
    description = (
        "JPEG XR (HD Photo, ISO/IEC 29199-2) reference codec: decode/encode "
        "libraries plus JxrDecApp/JxrEncApp tools"
    )
    license = "BSD-2-Clause"
    homepage = "https://github.com/4creators/jxrlib"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("image", "codec", "jpeg-xr", "jxr")

    # Static-only (upstream SHARED=1 .so rules carry no soname and the
    # house packages use static defaults); ada-bar-codes precedent.
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        # Pure-C package: C++ std/libcxx do not affect the artifact.
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def validate(self):
        # R32: only the OHOS/Linux family is validated.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "jxrlib %s supports Linux and OHOS, got os=%s"
                % (self.version, self.settings.os))

    def layout(self):
        # In-tree build (aescrypt precedent): the upstream Makefile builds
        # via $(CURDIR) relative paths; Conan 2.29 basic_layout's separate
        # build-release/ folder would not contain the sources.
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Patch at source time: Conan copies sources into the build folder
        # before generate()/build(), so patches applied there would be lost.
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        # Upstream CFLAGS keep the mandatory -D__ANSI__/-DDISABLE_PERF_
        # MEASUREMENT defines and include paths (R1: minimal flags); the
        # EXTRA_* variables patched into the Makefile carry the Conan
        # toolchain values (R33: no bare worker shell envs). Serial make:
        # -j enables GNU make's FIFO jobserver, and mkfifo is not
        # permitted on the device workspace filesystem (HMDFS).
        self.run(
            'make EXTRA_CFLAGS="$CFLAGS $CPPFLAGS" EXTRA_LDFLAGS="$LDFLAGS"',
            env="conanbuild", cwd=self.build_folder)

    def package(self):
        src = self.source_folder
        build = os.path.join(self.build_folder, "build")
        lib = os.path.join(self.package_folder, "lib")
        bin_dir = os.path.join(self.package_folder, "bin")
        for libname in ("jpegxr", "jxrglue"):
            copy(self, "lib%s.a" % libname, build, lib, keep_path=False)
            copy(self, "lib%s.so*" % libname, build, lib, keep_path=False)
        copy(self, "JxrDecApp", build, bin_dir, keep_path=False)
        copy(self, "JxrEncApp", build, bin_dir, keep_path=False)
        # Header layout mirrors the upstream `make install` tree so the
        # libjxr.pc include flags keep working for pkg-config consumers.
        inc = os.path.join(self.package_folder, "include", "libjxr")
        copy(self, "*.h", os.path.join(src, "common", "include"),
             os.path.join(inc, "common"))
        copy(self, "*.h", os.path.join(src, "image", "sys"),
             os.path.join(inc, "image"))
        copy(self, "*.h", os.path.join(src, "image", "decode"),
             os.path.join(inc, "image"))
        copy(self, "*.h", os.path.join(src, "image", "encode"),
             os.path.join(inc, "image"))
        copy(self, "*.h", os.path.join(src, "image", "x86"),
             os.path.join(inc, "image", "x86"))
        copy(self, "*.h", os.path.join(src, "jxrgluelib"),
             os.path.join(inc, "glue"))
        copy(self, "*.h", os.path.join(src, "jxrtestlib"),
             os.path.join(inc, "test"))
        copy(self, "LICENSE", src, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Mirrors upstream libjxr.pc Cflags: flattened header groups plus
        # the two ABI-locking defines consumers must compile with.
        inc = os.path.join("include", "libjxr")
        self.cpp_info.includedirs = [
            os.path.join(inc, "common"),
            os.path.join(inc, "image"),
            os.path.join(inc, "image", "x86"),
            os.path.join(inc, "glue"),
            os.path.join(inc, "test"),
        ]
        # Static link order: glue sits on top of the codec.
        self.cpp_info.libs = ["jxrglue", "jpegxr"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.defines = ["__ANSI__", "DISABLE_PERF_MEASUREMENT"]
        self.cpp_info.bindirs = ["bin"]
