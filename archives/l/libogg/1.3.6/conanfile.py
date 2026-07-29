#!/usr/bin/env python3
"""Conan recipe for libogg 1.3.6."""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get


class LiboggConan(ConanFile):
    name = "libogg"
    version = "1.3.6"
    description = "Ogg multimedia container library"
    license = "BSD-3-Clause"
    homepage = "https://xiph.org/ogg/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _sign_ohos_elf(self, path):
        tools = {}
        for name in ("llvm-readelf", "llvm-objcopy", "binary-sign-tool"):
            tools[name] = shutil.which(name) or os.path.join("/data/service/hnp/bin", name)
            if not os.path.isfile(tools[name]):
                raise ConanException(f"Required OHOS tool is missing: {name}")
        temporary = path + ".libogg-signed"
        subprocess.run(
            [tools["binary-sign-tool"], "sign", "-inFile", path,
             "-outFile", temporary, "-selfSign", "1"], check=True, timeout=60
        )
        sections = subprocess.run(
            [tools["llvm-readelf"], "-SW", temporary], check=True,
            capture_output=True, text=True, timeout=30
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException(f"Signed ELF has invalid .codesign count: {path}")
        os.chmod(temporary, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(temporary, path)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["BUILD_TESTING"] = True
        tc.variables["INSTALL_DOCS"] = False
        tc.variables["INSTALL_PKG_CONFIG_MODULE"] = True
        tc.variables["INSTALL_CMAKE_PACKAGE_MODULE"] = True
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            suffix = ".exe" if self.settings.os == "Windows" else ""
            for name in ("test_bitwise", "test_framing"):
                executable = os.path.join(self.build_folder, name + suffix)
                if str(self.settings.os) == "OHOS":
                    self._sign_ohos_elf(executable)
                self.run(f'"{executable}"')

    def package(self):
        CMake(self).install()
        if str(self.settings.os) == "OHOS" and self.options.shared and can_run(self):
            self._sign_ohos_elf(os.path.join(self.package_folder, "lib", "libogg.so"))

    def package_info(self):
        self.cpp_info.libs = ["ogg"]
        self.cpp_info.set_property("cmake_file_name", "Ogg")
        self.cpp_info.set_property("cmake_target_name", "Ogg::ogg")
        self.cpp_info.set_property("pkg_config_name", "ogg")
