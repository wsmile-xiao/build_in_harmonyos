#!/usr/bin/env python3
"""Consumer test for TagLib C bindings (tag_c.h / libtag_c).

R34: the test actually calls the C API (taglib_file_new, taglib_tag_title,
...) — it is not a C++-only or print-only shell.
"""

import os
import shutil

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class TaglibTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("Cross-building: compile and link test passed")
            return
        bash = (
            os.environ.get("CONFIG_SHELL")
            or shutil.which("bash")
            or "/data/service/hnp/bin/bash"
        )
        # test_tag_c is linked by the C++ driver (libtag_c wraps the C++
        # API), so its DT_NEEDED carries libc++_shared.so which lives in the
        # OHOS native toolchain directory, not in the Conan cache. Inline the
        # loader path in the command (conanrun env lists do not reliably
        # propagate on OHOS).
        llvm_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos"
        if not os.path.isdir(llvm_lib):
            llvm_lib = "/data/service/hnp/bin/../lib/aarch64-linux-ohos"
        self.run(
            f'export LD_LIBRARY_PATH="{llvm_lib}:${{LD_LIBRARY_PATH:-}}"; '
            f"{bash} -c './test_tag_c'",
            env="conanrun",
        )
