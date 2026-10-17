#!/usr/bin/env python3
"""Consumer test_package for volk/3.3.0 (R34/R53).

1. Builds and runs a real consumer that links the packaged libvolk and calls
   volk_get_machine(), volk_get_alignment(), volk_malloc()/volk_free() and the
   SIMD-dispatched volk_32f_s32f_multiply_32f kernel with assertions.
2. HarmonyOS-specific check: the packaged libvolk.so must carry a .codesign
   section, otherwise the OHOS dynamic loader refuses to load it (E077).
"""

import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class VolkTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            # Same platform alignment as the package recipe: CMake does not
            # know the HarmonyOS host system.
            tc.variables["CMAKE_SYSTEM_NAME"] = "OHOS"
            tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 1) real consumer run with the OHOS runtime environment
        binary = os.path.join(self.cpp.build.bindirs[0], "test_volk")
        self.run(binary, env="conanrun")

        # 2) HarmonyOS ELF signature check on the packaged library (E077)
        dep = self.dependencies[self.tested_reference_str]
        libdir = os.path.join(dep.package_folder, dep.cpp_info.libdirs[0])
        candidates = sorted(glob.glob(os.path.join(libdir, "libvolk.so*")))
        real_libs = [p for p in candidates if not os.path.islink(p)]
        library = real_libs[0] if real_libs else (candidates[0] if candidates else None)
        if not library:
            raise ConanException("packaged libvolk.so not found in %s" % libdir)
        readelf = (shutil.which("llvm-readelf")
                   or "/data/service/hnp/bin/llvm-readelf"
                   or shutil.which("readelf"))
        if not readelf:
            raise ConanException("no readelf/llvm-readelf available for the codesign check")
        self.run('"%s" -S "%s" | grep -q codesign' % (readelf, library))
