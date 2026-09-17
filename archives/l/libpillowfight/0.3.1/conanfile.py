from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, CMakeDeps, CMake, cmake_layout
from conan.tools.files import get, save, apply_conandata_patches
import os


class LibpillowfightConan(ConanFile):
    name = "libpillowfight"
    version = "0.3.1"
    license = "GPL-2.0-only"
    url = "https://gitlab.gnome.org/World/OpenPaperwork/libpillowfight"
    description = "A library for image processing algorithms (paper scan cleanup)"
    topics = ("image-processing", "paper-scan", "unpaper")
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = None

    def layout(self):
        cmake_layout(self, src_folder="src")

    def export_sources(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"][0], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def _generate_version_header(self):
        """Generate _version.h required by upstream build system."""
        version_content = (
            '#ifndef __VERSION_H\n'
            '#define __VERSION_H\n'
            f'#define INTERNAL_PILLOWFIGHT_VERSION "{self.version}"\n'
            '#endif\n'
        )
        version_dir = os.path.join(self.source_folder, "src", "pillowfight")
        os.makedirs(version_dir, exist_ok=True)
        save(self, os.path.join(version_dir, "_version.h"), version_content)

    def build(self):
        apply_conandata_patches(self)
        self._generate_version_header()
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["pillowfight"]
        self.cpp_info.includedirs = ["include"]
