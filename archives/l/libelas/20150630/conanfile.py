#!/usr/bin/env python3
"""Conan recipe for libelas 20150630 - Efficient Large-scale Stereo matching.

libelas computes disparity maps from rectified greyscale stereo image pairs
(Elas::process).  It is a small C++ library whose inner loops are hand written
x86 SSE2/SSE3 intrinsics.

OHOS notes
----------
* The upstream code is x86-only: ``elas.h``/``descriptor.cpp`` include
  ``<emmintrin.h>`` and ``elas.cpp`` uses ``_mm_*`` SSE2 intrinsics, while the
  bundled CMakeLists forces ``-msse3``; Debian only ever produced amd64
  binaries for this source for the same reason.  The portability patch includes
  SSE2NEON (DLTcollab, MIT) on non-x86 targets, which maps every intrinsic used
  to NEON.  The sources are compiled directly so the hard-coded ``-msse3`` is
  bypassed.
* SSE2NEON is fetched in ``source()`` from codeload.github.com (github.com is
  often unreachable from the device) at a pinned tag, and ``sse2neon.h`` is
  installed next to ``elas.h`` because the public header exposes ``__m128i`` in
  private method signatures; consumers therefore need the header too.
* No upstream test suite exists.  ``build()`` compiles the upstream ``elas``
  demo and runs ``./elas demo`` over the bundled ``img/`` pairs (the upstream
  documented verification) and ``test_package`` checks the disparity of a
  synthetic pair with a known shift.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"

_SOURCES = ("descriptor", "elas", "filter", "matrix", "triangle")
_EXPECTED_PAIRS = 7


class LibelasConan(ConanFile):
    name = "libelas"
    version = "20150630"
    description = ("LIBrary for Efficient LArge-scale Stereo matching: disparity "
                   "maps from rectified greyscale stereo pairs")
    license = "GPL-3.0-or-later"
    homepage = "http://www.cvlibs.net/software/libelas/"
    url = ""

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libelas OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        get(self, **self.conan_data["sse2neon"], strip_root=True, destination="sse2neon")
        copy(self, "sse2neon.h",
             src=os.path.join(self.source_folder, "sse2neon"),
             dst=self.source_folder, keep_path=False)

    def _compiler(self, name, fallback):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        return executables.get(name) or fallback

    def _compile(self, cxx, source, output, extra=""):
        src_dir = os.path.join(self.source_folder, "src")
        # -Wno-narrowing/-Wno-format mirror the Debian build-library patch:
        # elas.cpp uses C++11 initializer lists with int32_t -> float.
        self.run('"{}" -O3 -std=c++11 -fPIC -Wall -Wno-narrowing -Wno-format '
                 '-I"{}" -I"{}" {} -c "{}" -o "{}"'.format(
                     cxx, src_dir, self.source_folder, extra, source, output))

    def build(self):
        apply_conandata_patches(self)
        cxx = self._compiler("cpp", "clang++")
        src_dir = os.path.join(self.source_folder, "src")

        objects = []
        for name in _SOURCES:
            obj = os.path.join(self.build_folder, name + ".o")
            self._compile(cxx, os.path.join(src_dir, name + ".cpp"), obj)
            objects.append(obj)

        if self.options.shared:
            library = os.path.join(self.build_folder, "libelas.so")
            self.run('"{}" -shared -fPIC -Wl,-soname,libelas.so -o "{}" {}'.format(
                cxx, library, " ".join('"{}"'.format(o) for o in objects)))
        else:
            library = os.path.join(self.build_folder, "libelas.a")
            self.run('llvm-ar rcs "{}" {}'.format(
                library, " ".join('"{}"'.format(o) for o in objects)))

        # Build and run the upstream demo as functional evidence.  libc++ does
        # not pull <algorithm> transitively, so pull it in for main.cpp's max().
        demo_obj = os.path.join(self.build_folder, "main.o")
        self._compile(cxx, os.path.join(src_dir, "main.cpp"), demo_obj,
                      extra="-include algorithm")
        demo = os.path.join(self.build_folder, "elas-demo")
        if self.options.shared:
            self.run('"{}" -o "{}" "{}" -L"{}" -lelas -Wl,-rpath,"{}"'.format(
                cxx, demo, demo_obj, self.build_folder, self.build_folder))
        else:
            self.run('"{}" -o "{}" "{}" "{}"'.format(cxx, demo, demo_obj, library))

        image_dir = os.path.join(self.build_folder, "img")
        if not os.path.isdir(image_dir):
            shutil.copytree(os.path.join(self.source_folder, "img"), image_dir)
        log = os.path.join(self.build_folder, "upstream-elas-demo.log")
        self.run('"{}" demo > "{}" 2>&1'.format(demo, log), cwd=self.build_folder)
        produced = glob.glob(os.path.join(image_dir, "*_disp.pgm"))
        if len(produced) < 2 * _EXPECTED_PAIRS:
            raise ConanException(
                "upstream 'elas demo' produced {} disparity maps, expected {}".format(
                    len(produced), 2 * _EXPECTED_PAIRS))
        self.output.info("upstream 'elas demo' produced {} disparity maps".format(len(produced)))

    def package(self):
        include_dir = os.path.join(self.package_folder, "include")
        copy(self, "elas.h", src=os.path.join(self.source_folder, "src"), dst=include_dir)
        copy(self, "sse2neon.h", src=self.source_folder, dst=include_dir)
        lib_dir = os.path.join(self.package_folder, "lib")
        if self.options.shared:
            copy(self, "libelas.so", src=self.build_folder, dst=lib_dir)
        else:
            copy(self, "libelas.a", src=self.build_folder, dst=lib_dir)
        copy(self, "LICENSE", src=os.path.join(self.source_folder, "sse2neon"),
             dst=os.path.join(self.package_folder, "licenses", "sse2neon"),
             keep_path=False)
        copy(self, "README.TXT", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["elas"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "elas")
        self.cpp_info.set_property("cmake_target_name", "elas::elas")
