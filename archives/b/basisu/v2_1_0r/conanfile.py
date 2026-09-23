#!/usr/bin/env python3
"""Conan recipe — basisu (v2_1_0r)

Basis Universal GPU texture codec command-line compression tool.
Builds the basisu CLI tool and static encoding/transcoding libraries.

Homepage: https://github.com/BinomialLLC/basis_universal
License: Apache-2.0
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class BasisuConan(ConanFile):
    name = "basisu"
    version = "v2_1_0r"
    description = "Basis Universal GPU texture codec command-line compression tool"
    license = "Apache-2.0"
    homepage = "https://github.com/BinomialLLC/basis_universal"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/tree/main/archives/b/basisu/v2_1_0r"

    settings = "os", "compiler", "build_type", "arch"
    # The package ships a linkable static library (libbasisu_encoder.a) plus
    # headers, and additionally the basisu CLI tool (bin/basisu, declared in
    # commands.json type=tool). package_type reflects the linkable deliverable:
    # "static-library" keeps CMakeDeps propagating cpp_info (libs/includedirs)
    # to consumers — with "application" conan 2.29.1 omits cpp_info from the
    # generated *-data.cmake (INCLUDE_DIRS/LIBS empty) and test_package fails
    # with 'basis_universal/basisu_transcoder.h' file not found.
    package_type = "static-library"

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
        # OHOS musl: does not provide GNU-sig qsort_r → skip HAS_QSORT_R → patch uses C90 fallback
        if str(self.settings.os) != "OHOS":
            tc.preprocessor_definitions["HAS_QSORT_R"] = True
        tc.variables["BASISU_EXAMPLES"] = "OFF"
        tc.variables["BASISU_OPENCL"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        # Install the basisu CLI binary. Upstream CMakeLists.txt sets
        # CMAKE_RUNTIME_OUTPUT_DIRECTORY to ${CMAKE_CURRENT_SOURCE_DIR}/bin
        # (line 30), so with the default in-source output the binary lands in
        # the SOURCE tree, not the build tree. Search both locations so the
        # recipe keeps working if upstream ever changes the output directory,
        # and fail loudly instead of silently shipping a package without the
        # CLI tool (the primary deliverable per commands.json).
        candidates = [
            os.path.join(self.source_folder, "bin"),
            os.path.join(self.build_folder, "bin"),
            self.build_folder,
        ]
        bin_dir = next(
            (d for d in candidates if os.path.isfile(os.path.join(d, "basisu"))),
            None,
        )
        if bin_dir is None:
            raise ConanException(
                "basisu CLI binary not found in source_folder/bin, "
                "build_folder/bin or build_folder"
            )
        copy(self, "basisu", bin_dir, os.path.join(self.package_folder, "bin"))

        # Install the sole static library produced by upstream CMakeLists.txt:
        # add_library(basisu_encoder STATIC ${ENCODER_LIB_SRC_LIST}). The
        # ENCODER_LIB_SRC_LIST already includes transcoder/basisu_transcoder.cpp,
        # so libbasisu_encoder.a contains both the encoder and the transcoder
        # implementation.
        lib_dir = self.build_folder
        if os.path.isdir(lib_dir):
            copy(self, "libbasisu_encoder.a", lib_dir,
                 os.path.join(self.package_folder, "lib"))

        # Install upstream LDR test fixtures so test_package can run the real
        # upstream `basisu -test` suite. Only the 28 PNG inputs required by
        # -test/-test_ldr are shipped (~15 MB), not the full 43 MB test_files/ tree.
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
        trans_dir = os.path.join(self.source_folder, "transcoder")
        if os.path.isdir(trans_dir):
            copy(self, "*.h", trans_dir, os.path.join(self.package_folder, "include", "basis_universal"))

    def package_info(self):
        # Upstream builds a single static archive libbasisu_encoder.a
        # (add_library(basisu_encoder STATIC ${ENCODER_LIB_SRC_LIST})).
        # ENCODER_LIB_SRC_LIST already contains transcoder/basisu_transcoder.cpp,
        # so the transcoder implementation lives inside libbasisu_encoder.a.
        self.cpp_info.libs = ["basisu_encoder"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.system_libs = ["m", "pthread"]
        self.cpp_info.set_property("cmake_target_name", "basisu::basisu")
        self.cpp_info.bindirs = ["bin"]
