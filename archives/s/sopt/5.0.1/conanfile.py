import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import apply_conandata_patches, chdir, copy, export_conandata_patches, get


class SoptConan(ConanFile):
    name = "sopt"
    version = "5.0.1"
    description = "Sparse optimisation algorithms with Eigen and TIFF image support"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/astro-informatics/sopt"
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("eigen/3.4.0", transitive_headers=True)
        self.requires("libtiff/4.7.2", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        self.test_requires("catch2/3.8.1")

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, "17")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.set_property("libtiff", "cmake_file_name", "TIFF")
        deps.set_property("libtiff", "cmake_target_name", "TIFF::TIFF")
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables.update({
            "tests": True, "examples": True, "dompi": False,
            "openmp": False, "onnxrt": False, "benchmarks": False,
            "docs": False, "coverage": False, "NOEXPORT": True,
            "eigen_INCLUDE_DIR": self.dependencies["eigen"].cpp_info.includedirs[0],
            "TIFF_INCLUDE_DIR": self.dependencies["libtiff"].cpp_info.includedirs[0],
        })
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(cli_args=["--debug-find"])
        cmake.build()
        # Upstream image tests read CMAKE_INSTALL_PREFIX/test_data. Install
        # their original fixtures before testing; package() installs afresh.
        cmake.install()
        with chdir(self, self.build_folder):
            self.run("ctest --show-only=json-v1 > upstream-test-list.json")
        cmake.ctest(cli_args=["--output-on-failure", "--no-tests=error",
                             "--output-junit", "upstream-tests.xml"], env="conanrun")

    def package(self):
        CMake(self).install()
        copy(self, "LICENSE.txt", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["sopt"]
        self.cpp_info.bindirs = []
        self.cpp_info.set_property("cmake_file_name", "sopt")
        self.cpp_info.set_property("cmake_target_name", "sopt::sopt")
