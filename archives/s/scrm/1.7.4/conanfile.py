"""scrm's original C++ sources and complete registered CppUnit suites."""
import hashlib
import os
from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, unzip


class ScrmConan(ConanFile):
    name = "scrm"
    version = "1.7.4"
    license = "GPL-3.0-or-later"
    description = "Sequential coalescent with recombination simulator"
    homepage = "https://scrm.github.io"
    url = "https://github.com/scrm/scrm"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "CMakeLists.txt"

    def build_requirements(self):
        self.test_requires("cppunit/1.15.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("Supported targets: Linux and OHOS")

    def layout(self):
        cmake_layout(self)

    def source(self):
        archive = os.environ.get("SCRM_SOURCE_ARCHIVE")
        if archive:
            with open(archive, "rb") as stream:
                actual = hashlib.file_digest(stream, "sha256").hexdigest()
            if actual != self.conan_data["sources"]["sha256"]:
                raise ConanException("SCRM_SOURCE_ARCHIVE SHA-256 mismatch")
            unzip(self, archive, strip_root=True)
        else:
            get(self, **self.conan_data["sources"], strip_root=True)
        # Conan may materialize exported sources directly in source_folder.
        # copy() rejects identical source/destination, even for a preserved overlay.
        if os.path.realpath(self.export_sources_folder) != os.path.realpath(self.source_folder):
            copy(self, "CMakeLists.txt", self.export_sources_folder, self.source_folder)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["SCRM_BUILD_TESTS"] = True
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if cross_building(self):
            self.output.warning("Cross build: target runtime tests NOT RUN")
        else:
            cmake.ctest(cli_args=["--verbose", "--output-on-failure"])

    def package(self):
        CMake(self).install()
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.buildenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
