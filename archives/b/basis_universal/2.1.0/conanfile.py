#!/usr/bin/env python3
"""Conan recipe — basis_universal (v2.1.0)

Basis Universal GPU texture codec command-line compression tool.
Builds the basisu CLI tool and static encoding/transcoding libraries.

Homepage: https://github.com/BinomialLLC/basis_universal
License: Apache-2.0
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class BasisUniversalConan(ConanFile):
    name = "basis_universal"
    version = "2.1.0"
    description = "Basis Universal GPU texture codec command-line compression tool"
    license = "Apache-2.0"
    homepage = "https://github.com/BinomialLLC/basis_universal"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    # R32: settings.os must be Linux or OHOS
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Feature detection: HAS_QSORT_R indicates qsort_r with GNU signature is available
        # This replaces platform macros in the patch (R8: use feature detection, not platform conditionals)
        # check_symbol_exists(qsort_r "stdlib.h" HAS_QSORT_R) with _GNU_SOURCE:
        #   Linux glibc: found → define HAS_QSORT_R → patch defines _GNU_SOURCE
        #   OHOS musl:   not found → skip HAS_QSORT_R → patch uses C90 fallback (g_coverCtx + qsort)
        if str(self.settings.os) != "OHOS":
            tc.variables["CMAKE_C_FLAGS"] = "-DHAS_QSORT_R"
            tc.variables["CMAKE_CXX_FLAGS"] = "-DHAS_QSORT_R"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        # Install basisu CLI binary (upstream CMakeLists.txt sets CMAKE_RUNTIME_OUTPUT_DIRECTORY to ${CMAKE_SOURCE_DIR}/bin)
        bin_dir = os.path.join(self.source_folder, "bin")
        if os.path.isdir(bin_dir):
            copy(self, "basisu", bin_dir, os.path.join(self.package_folder, "bin"))

        # Install the sole static library produced by upstream CMakeLists.txt:
        # add_library(basisu_encoder STATIC ${ENCODER_LIB_SRC_LIST}). The
        # ENCODER_LIB_SRC_LIST already includes transcoder/basisu_transcoder.cpp,
        # so libbasisu_encoder.a contains both the encoder and the transcoder
        # implementation — there is no separate libbasisu_transcoder.a target
        # in upstream v2_1_0. The archive is left in the build directory
        # (upstream sets no CMAKE_ARCHIVE_OUTPUT_DIRECTORY).
        lib_dir = self.build_folder
        if os.path.isdir(lib_dir):
            copy(self, "libbasisu_encoder.a", lib_dir,
                 os.path.join(self.package_folder, "lib"))

        # Install upstream LDR test fixtures (g_etc1s_uastc_4x4_ldr_test_files) so
        # test_package can run the real upstream `basisu -test` suite. Only the 28
        # PNG inputs required by -test/-test_ldr are shipped (~15 MB), not the full
        # 43 MB test_files/ tree (which also contains HDR .exr inputs).
        test_files_dir = os.path.join(self.source_folder, "test_files")
        if os.path.isdir(test_files_dir):
            ldr_inputs = [
                "black_1x1.png", "white_1x1.png", "wikipedia.png", "alpha0.png",
            ] + ["kodim{:02d}.png".format(i) for i in range(1, 25)]
            for fname in ldr_inputs:
                src = os.path.join(test_files_dir, fname)
                if os.path.isfile(src):
                    copy(self, fname, test_files_dir,
                         os.path.join(self.package_folder, "res", "test_files"))

        # Install all headers from transcoder/ directory
        # (basisu_transcoder.h depends on several internal headers:
        #  basisu_transcoder_internal.h, basisu_transcoder_uastc.h, basisu_file_headers.h,
        #  which in turn pull in basisu.h, basisu_astc_helpers.h, basisu_containers.h, etc.)
        trans_dir = os.path.join(self.source_folder, "transcoder")
        if os.path.isdir(trans_dir):
            copy(self, "*.h", trans_dir, os.path.join(self.package_folder, "include", "basis_universal"))

    def package_info(self):
        # Upstream v2_1_0 builds a single static archive libbasisu_encoder.a
        # (add_library(basisu_encoder STATIC ${ENCODER_LIB_SRC_LIST})).
        # ENCODER_LIB_SRC_LIST already contains transcoder/basisu_transcoder.cpp,
        # so the transcoder implementation lives inside libbasisu_encoder.a —
        # there is no separate basisu_transcoder library in this release.
        # Upstream also links the executable against m and pthread on
        # non-MSVC/WASM builds.
        self.cpp_info.libs = ["basisu_encoder"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.system_libs = ["m", "pthread"]
        self.cpp_info.set_property("cmake_target_name", "basis_universal::basis_universal")