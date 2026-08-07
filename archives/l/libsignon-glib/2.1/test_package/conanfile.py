import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.gnu import PkgConfigDeps


class LibsignonGlibTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "PkgConfigDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Build the library path from all dependencies
        ld_paths = []
        for dep_name in ["libsignon-glib", "glib"]:
            if dep_name in self.dependencies:
                dep = self.dependencies[dep_name]
                libdirs = dep.cpp_info.aggregated_components().libdirs
                ld_paths.extend(libdirs)

        ld_path = ":".join(ld_paths)
        current_ld = os.environ.get("LD_LIBRARY_PATH", "")
        if current_ld:
            ld_path = ld_path + ":" + current_ld

        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_libsignon-glib")
        self.run(f'LD_LIBRARY_PATH="{ld_path}" {test_bin}', env="conanrun")
