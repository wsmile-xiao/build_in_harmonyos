"""FAAD2 2.11.4 AAC decoder library for HarmonyOS PC."""

import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import copy, get


class Faad2Conan(ConanFile):
    name = "faad2"
    version = "2.11.4"
    package_type = "library"
    description = "FAAD2 MPEG-2 and MPEG-4 AAC decoder"
    homepage = "https://github.com/FreewareAdvancedAudio/faad2"
    license = "GPL-2.0-or-later"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        source = dict(self.conan_data["sources"][self.version])
        local_archive = os.environ.get("FAAD2_SOURCE_ARCHIVE")
        if local_archive:
            archive = Path(local_archive).resolve(strict=True)
            if not archive.is_file():
                raise ConanInvalidConfiguration("local source archive is not a file")
            source["url"] = archive.as_uri()
            source["filename"] = archive.name
        get(self, **source, strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        # The dependency package exposes the decoder library, not the CLI.
        tc.variables["FAAD_BUILD_CLI"] = False
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream 2.11.4 defines no CTest/add_test or other test target.

    def package(self):
        CMake(self).install()
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["faad"]
        self.cpp_info.system_libs = ["m"] if self.settings.os != "Windows" else []
        self.cpp_info.set_property("cmake_file_name", "faad2")
        self.cpp_info.set_property("cmake_target_name", "faad2::faad2")
        self.cpp_info.set_property("pkg_config_name", "faad2")
        self.runenv_info.prepend_path("LD_LIBRARY_PATH",
                                      os.path.join(self.package_folder, "lib"))
