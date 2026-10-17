#!/usr/bin/env python3
"""Conan recipe for mrcal 2.5.2 - camera calibration and geometry library.

Upstream builds through its own ``mrbuild`` framework (not shipped in the
tarball; fetched here from its pinned v1.16 release) and needs re2c + perl to
generate two sources.  Two files are generated at build time:

* ``cameramodel-parser_GENERATED.c`` (re2c, from cameramodel-parser.re)
* ``minimath/minimath_generated.h``   (perl, from minimath_generate.pl)

The Python-facing glue ``python-cameramodel-converter.c`` is dropped (it needs
CPython + numpy development headers and is only used by the Python bindings;
nothing in the C library core references it) - see the patch.

The recipe builds ``libmrcal.so`` and the pure-C test programs that upstream
``test.sh`` runs without Python, and executes them.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, download, export_conandata_patches, get, unzip

required_conan_version = ">=2.0"

MRBUILD_URL = "https://codeload.github.com/dkogan/mrbuild/tar.gz/refs/tags/v1.16"
MRBUILD_SHA256 = "f2ae97ce0b6a2d5bfab132a27757c269cb378c22bc4b5e1e0e36380abc954433"

# Pure-C tests that upstream test.sh runs directly (no Python).
C_TESTS = (
    "test/test-cahvor",
    "test/test-heap",
    "test/test-lensmodel-string-manipulation",
    "test/test-parser-cameramodel",
)


class MrcalConan(ConanFile):
    name = "mrcal"
    version = "2.5.2"
    description = "Camera calibration and geometry library"
    license = "Apache-2.0"
    homepage = "https://mrcal.secretsauce.net/"
    url = ""

    package_type = "shared-library"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "mrcal OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def requirements(self):
        self.requires("libdogleg/0.18")
        self.requires("suitesparse/7.8.3")
        self.requires("lapack/3.12.1")
        self.requires("libpng/1.6.58.3")
        self.requires("libjpeg-turbo/3.2.0")
        self.requires("stb_image/2.30")

    def build_requirements(self):
        self.tool_requires("re2c/4.3.1")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        download(self, MRBUILD_URL, "mrbuild-1.16.tar.gz",
                 sha256=MRBUILD_SHA256)
        unzip(self, "mrbuild-1.16.tar.gz", destination="mrbuild", strip_root=True)

    def _compiler(self, name, fallback):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        return executables.get(name) or fallback

    def build(self):
        apply_conandata_patches(self)
        cc = self._compiler("c", "clang")
        cxx = self._compiler("cpp", "clang++")
        bindir = os.path.dirname(cc)
        ar = os.path.join(bindir, "llvm-ar")

        incs, libdirs = [], []
        stb_include = None
        for dep in self.dependencies.values():
            incs.extend(dep.cpp_info.includedirs)
            libdirs.extend(dep.cpp_info.libdirs)
            for i in dep.cpp_info.includedirs:
                if os.path.isfile(os.path.join(i, "stb_image.h")):
                    stb_include = i
        # mrcal includes <stb/stb_image.h>; the stb_image package installs a
        # bare stb_image.h, so provide a stb/ shim directory.
        if stb_include:
            shim = os.path.join(self.source_folder, "_stb_shim", "stb")
            os.makedirs(shim, exist_ok=True)
            shutil.copy(os.path.join(stb_include, "stb_image.h"),
                        os.path.join(shim, "stb_image.h"))
            incs.append(os.path.join(self.source_folder, "_stb_shim"))
        incs = list(dict.fromkeys(incs))
        libdirs = list(dict.fromkeys(libdirs))
        incflags = " ".join('-I"%s"' % i for i in incs)
        libflags = " ".join('-L"%s"' % i for i in libdirs)

        # Generate the two build-time sources.
        re2c = os.path.join(self.dependencies.build["re2c"].cpp_info.bindirs[0],
                            "re2c")
        self.run('"{}" cameramodel-parser.re > cameramodel-parser_GENERATED.c'
                 .format(re2c), cwd=self.source_folder)
        self.run('perl minimath/minimath_generate.pl > minimath/minimath_generated.h',
                 cwd=self.source_folder)

        cflags = '{} -O2 -fPIC -DSTB_IMAGE_IMPLEMENTATION=1'.format(incflags)
        cxxflags = '{} -O2 -fPIC -std=gnu++14'.format(incflags)
        ldflags = libflags
        ldlibs = ("-ldogleg -lcholmod -lamd -lcolamd -lccolamd "
                  "-lsuitesparseconfig -lopenblas -lpng -ljpeg -lm")
        # mrbuild rejects %FLAGS as make arguments; they must be env variables.
        env = ('CC="{cc}" CXX="{cxx}" AR="{ar}" RANLIB="{ranlib}" '
               'CFLAGS="{cflags}" CXXFLAGS="{cxxflags}" CCXXFLAGS="{shared}" '
               'LDFLAGS="{ldflags}" LDLIBS="{ldlibs}" '
               'USE_LIBELAS=0 USE_LOCAL_STB_IMPLEMENTATION=1 '
               'OBJCOPY=llvm-objcopy NM=llvm-nm'
               .format(cc=cc, cxx=cxx, ar=ar,
                       ranlib=os.path.join(bindir, "llvm-ranlib"),
                       cflags=cflags, cxxflags=cxxflags, shared=incflags,
                       ldflags=ldflags, ldlibs=ldlibs))
        common = env + " make -j1 "
        self.run(common + "libmrcal.so", cwd=self.source_folder)
        self.run(common + " ".join(C_TESTS), cwd=self.source_folder)
        runenv = 'LD_LIBRARY_PATH="{}:${{LD_LIBRARY_PATH:-}}" '.format(
            ":".join(libdirs))
        for test in C_TESTS:
            self.run(runenv + '"./%s"' % test, cwd=self.source_folder)
            self.output.info("upstream %s passed" % os.path.basename(test))

    def package(self):
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        copy(self, "libmrcal.so*", self.source_folder,
             os.path.join(self.package_folder, "lib"))
        for h in ("mrcal.h", "image.h", "internal.h", "basic-geometry.h",
                  "poseutils.h", "triangulation.h", "types.h", "stereo.h",
                  "heap.h"):
            copy(self, h, self.source_folder,
                 os.path.join(self.package_folder, "include"))
        copy(self, "minimath/*.h", self.source_folder,
             os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["mrcal"]
