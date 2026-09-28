#!/usr/bin/env python3
"""Conan recipe — scrappie 1.4.2 (OHOS aarch64 adaptation).

scrappie is Oxford Nanopore Technologies' basecaller research library
(basecaller CLI + libscrappie static library).

Upstream build: CMake. Key OHOS adaptations:
  - x86 SSE intrinsics (util.h -> <immintrin.h>, sse_mathfun.h ->
    <xmmintrin.h>/<emmintrin.h>) are translated to NEON with sse2neon shim
    headers (same approach Debian uses with simde/sse2neon for arm64).
  - GNU argp is not in musl libc -> argp-standalone.
  - upstream CMake hardcodes -march=native and cmake_minimum_required 2.8.12
    (hard error on CMake 4) -> patch 0001.
  - upstream CMake resolves BLAS/HDF5 by raw linker name under OPENBLAS_ROOT /
    HDF5_ROOT; recipe injects the Conan package folders there and adds the
    hdf5 transitive libs (sz, z) via SCRAPPIE_EXTRA_LIBS.
  - cunit is only needed to link the upstream unit-test binary -> test_requires.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ScrappieConan(ConanFile):
    name = "scrappie"
    version = "1.4.2"
    description = ("Scrappie: nanopore basecaller research library and CLI "
                   "from Oxford Nanopore Technologies")
    license = "MPL-2.0"
    homepage = "https://github.com/nanoporetech/scrappie"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # BLAS (upstream links -lopenblas / -lblas via OPENBLAS_ROOT)
        self.requires("openblas/0.3.34")
        # HDF5 (fast5 read interface of the CLI)
        self.requires("hdf5/1.14.6")
        # GNU argp: glibc-only, musl (OHOS) has none -> argp-standalone
        self.requires("argp-standalone/1.5.0")
        # x86 SSE -> NEON translation for sse_mathfun.h (header-only)
        self.requires("sse2neon/1.9.1")

    def validate(self):
        # R32: os must accept both Linux and OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidComponent("Unsupported os: %s" % self.settings.os)

    def build_requirements(self):
        # Upstream unit tests (src/test/*) link against CUnit — test-only,
        # not propagated to consumers.
        self.test_requires("cunit/2.1-3")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    @staticmethod
    def _abs_dirs(dep, dirs):
        """cpp_info dirs may be package-relative; make them absolute."""
        return [d if os.path.isabs(d) else os.path.join(dep.package_folder, d)
                for d in dirs]

    @staticmethod
    def _write_sse_shim(dirpath):
        """Write x86 intrinsics shim headers translating to NEON.

        util.h includes <immintrin.h>, sse_mathfun.h <xmmintrin.h>/
        <emmintrin.h>. clang only ships those for x86 targets, so map all
        three to sse2neon.h (x86 SSE -> ARM NEON). sse_mathfun.h and util.h
        additionally use the GCC builtin vector type __v4sf, which clang
        does not predefine on aarch64 — declare it via the generic vector
        extension (same 16-byte float vector as sse2neon's __m128)."""
        os.makedirs(dirpath, exist_ok=True)
        content = (
            "#pragma once\n"
            "#include <sse2neon.h>\n"
            "#ifndef SCRAPPIE_SSE_SHIM_V4SF\n"
            "#define SCRAPPIE_SSE_SHIM_V4SF\n"
            "typedef float __v4sf __attribute__((vector_size(16)));\n"
            "#endif\n"
        )
        for header in ("immintrin.h", "xmmintrin.h", "emmintrin.h"):
            with open(os.path.join(dirpath, header), "w") as f:
                f.write(content)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: system-name libraries default to static
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # E187 belt-and-braces: patch 0001 raises the minimum to 3.5 already;
        # this flag keeps the build resilient if the patch context shifts.
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"

        # Upstream CMake resolves BLAS/HDF5 by raw linker name under these
        # root dirs (include_directories + link_directories).
        tc.variables["OPENBLAS_ROOT"] = self.dependencies["openblas"].package_folder
        tc.variables["HDF5_ROOT"] = self.dependencies["hdf5"].package_folder

        # libhdf5 (static) needs its szip-compat layer and zlib; upstream has
        # no find_package, so pass them explicitly. OHOS hardening denies
        # exec-mmap of DSOs living outside trusted paths for processes whose
        # own binary is not bundled, and the build tree lives on HMDFS
        # (/storage) — shared conan-store libs cannot be loaded at test
        # runtime. Patch 0001 therefore prefers libopenblas.a / libhdf5.a
        # under *_ROOT, and argp/cunit/sz are linked by absolute .a path.
        # zlib stays name-based: the system libz.so is exec-allowed.
        dep = self.dependencies["libaec"]
        tc.variables["SCRAPPIE_EXTRA_LIBS"] = self._static_lib(
            dep, "libsz.a")

        tc.variables["SCRAPPIE_ARGP_LIB"] = self._static_lib(
            self.dependencies["argp-standalone"], "libargp.a")
        tc.variables["SCRAPPIE_CUNIT_LIB"] = self._static_lib(
            self.dependencies["cunit"], "libcunit.a")

        # sse2neon shim: clang's builtin x86 intrinsics headers hard-error on
        # aarch64, so put a shim dir first on the include path mapping
        # immintrin.h/xmmintrin.h/emmintrin.h to sse2neon.h.
        shim = os.path.join(self.build_folder, "sse2neon_shim")
        self._write_sse_shim(shim)
        sse2neon_inc = self._abs_dirs(
            self.dependencies["sse2neon"],
            self.dependencies["sse2neon"].cpp_info.includedirs)

        extra_cflags = ([f"-I{shim}"]
                        + [f"-I{d}" for d in sse2neon_inc]
                        # decode.c hard-errors without __SSE2__ and defines a
                        # redundant _mm_mullo_epi32 fallback without __SSE4_1__
                        # (would collide with sse2neon's own). sse2neon emulates
                        # both instruction sets, so declare them available.
                        + ["-D__SSE2__", "-D__SSE4_1__"])
        extra_ldflags = []
        for ref in ("argp-standalone", "cunit"):
            dep = self.dependencies[ref]
            for d in self._abs_dirs(dep, dep.cpp_info.includedirs):
                extra_cflags.append(f"-I{d}")

        tc.extra_cflags.extend(extra_cflags)
        # Upstream CMakeLists builds CMAKE_C_FLAGS_RELEASE from
        # ${CMAKE_C_FLAGS}, so toolchain cflags flow into every configuration.
        tc.generate()

    @staticmethod
    def _static_lib(dep, filename):
        """Absolute path of a static library inside a dependency package."""
        for d in ScrappieConan._abs_dirs(dep, dep.cpp_info.libdirs):
            candidate = os.path.join(d, filename)
            if os.path.exists(candidate):
                return candidate
        raise ConanException(
            "%s not found in %s" % (filename, dep.package_folder))

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # R51: actually run the upstream CTest suite (20 registered tests).
        # All dep libs except system libz are statically linked in, so no
        # runtime environment is needed.
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

        # Ship the sse2neon compat shim with the package: the installed
        # public headers (scrappie_matrix.h, util.h, ...) still include
        # <immintrin.h>/<xmmintrin.h>/<emmintrin.h>, which clang only
        # provides for x86 targets. Consumers on aarch64 need the shim on
        # their include path (see generate()).
        compat = os.path.join(self.package_folder, "include", "sse2neon_compat")
        os.makedirs(compat, exist_ok=True)
        sse2neon_pkg = self.dependencies["sse2neon"]
        src_header = None
        for d in self._abs_dirs(sse2neon_pkg, sse2neon_pkg.cpp_info.includedirs):
            candidate = os.path.join(d, "sse2neon.h")
            if os.path.exists(candidate):
                src_header = candidate
                break
        if src_header is None:
            raise ConanException("sse2neon.h not found in sse2neon package")
        copy(self, "sse2neon.h", os.path.dirname(src_header), compat)
        self._write_sse_shim(compat)

    def package_info(self):
        self.cpp_info.libs = ["scrappie"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.system_libs = ["m"]
        # aarch64 consumers must resolve <immintrin.h> etc. to the shim
        if self.settings.arch == "armv8":
            self.cpp_info.includedirs.append(
                os.path.join("include", "sse2neon_compat"))
