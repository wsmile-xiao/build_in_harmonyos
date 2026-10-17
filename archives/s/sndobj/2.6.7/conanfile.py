import os
from pathlib import Path

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, patch


class SndobjConan(ConanFile):
    name = "sndobj"
    version = "2.6.7"
    description = "Sound Object Library for audio synthesis and processing"
    license = "GPL-2.0-or-later"
    homepage = "https://sndobj.sourceforge.net/sndobj.html"
    url = "https://sourceforge.net/projects/sndobj/"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*"

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
        local_archive = os.environ.get("SNDOBJ_SOURCE_ARCHIVE")
        if local_archive:
            archive = Path(local_archive).resolve(strict=True)
            source["url"] = archive.as_uri()
            source["filename"] = archive.name
        get(self, **source, strip_root=True)
        patch(self, base_path=self.source_folder,
              patch_file=os.path.join(self.export_sources_folder, "patches",
                                      "0001-src-SndWaveX.h.patch"), strip=1)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["SNDOBJ_SOURCE_ROOT"] = self.source_folder.replace("\\", "/")
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder=os.path.join(self.export_sources_folder, "patches"))
        cmake.build()

    def package(self):
        CMake(self).install()
        copy(self, "License.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["sndobj"]
        self.cpp_info.defines = ["NO_RTIO"]
        self.cpp_info.set_property("cmake_file_name", "sndobj")
        self.cpp_info.set_property("cmake_target_name", "sndobj::sndobj")
        if not self.options.shared and str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "m"]
