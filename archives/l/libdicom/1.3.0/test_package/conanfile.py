#!/usr/bin/env python3
"""Conan test_package — consumer-level verification for libdicom 1.3.0.

Builds a small consumer program against the installed libdicom package and
verifies it can parse a real DICOM file: opens the file metadata, looks up
the Transfer Syntax UID element (0002,0010) with the public libdicom API
(dcm_filehandle_create_from_file / dcm_filehandle_get_file_meta /
dcm_dataset_get / dcm_element_get_value_string / dcm_filehandle_get_transfer_syntax_uid /
dcm_dataset_foreach), and prints the value.

The DICOM sample travels as base64 text (sm_image.dcm.b64, upstream sample
data) because GitCode PR diffs cannot carry binary blobs — the .diff endpoint
emits "Binary files differ" without GIT binary patch data, which breaks the
CI checkout-pr `git apply` step.  test() decodes it to a temp file before
running the consumer binary.

This is an L1 smoke test: it must fail if the library headers or the shared
object are unusable.
"""
import base64
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibdicomTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    exports_sources = "CMakeLists.txt", "test_libdicom.c", "data/*"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Decode the base64 DICOM sample to a temp file (text-safe transport).
        b64_src = os.path.join(self.source_folder, "data", "sm_image.dcm.b64")
        dcm = os.path.join(self.build_folder, "sm_image.dcm")
        with open(b64_src, "r", encoding="ascii") as f:
            with open(dcm, "wb") as out:
                out.write(base64.b64decode(f.read()))

        # Inline LD_LIBRARY_PATH (conan run env lists do not take effect on
        # OHOS — verified pattern from acsccid/1.1.13).
        lib_dir = os.path.join(
            self.dependencies["libdicom"].package_folder, "lib"
        )
        exe = os.path.join(self.cpp.build.bindirs[0], "test_libdicom")
        self.run(f'LD_LIBRARY_PATH="{lib_dir}" "{exe}" "{dcm}"')
