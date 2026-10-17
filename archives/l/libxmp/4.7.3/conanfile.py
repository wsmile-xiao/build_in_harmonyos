import os
from pathlib import Path
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv


class LibxmpConan(ConanFile):
    name = "libxmp"
    version = "4.7.3"
    package_type = "library"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/libxmp/libxmp"
    description = "Tracker module playback library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "ohos-soname.cmake"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        source = dict(self.conan_data["sources"][self.version])
        local = os.environ.get("LIBXMP_SOURCE_ARCHIVE")
        if local:
            source["url"] = Path(local).resolve(strict=True).as_uri()
        # The immutable codeload URL ends in a commit SHA, not an archive
        # extension. Preserve its hash while giving Conan the actual format.
        source["filename"] = "libxmp-4.7.3.tar.gz"
        get(self, **source, strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED"] = bool(self.options.shared)
        tc.variables["BUILD_STATIC"] = not bool(self.options.shared)
        tc.variables["LIBXMP_PIC"] = bool(self.options.get_safe("fPIC", True))
        tc.variables["WITH_UNIT_TESTS"] = True
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.10"
        if self.settings.os == "OHOS":
            tc.variables["CMAKE_PROJECT_INCLUDE"] = os.path.join(self.source_folder, "ohos-soname.cmake")
            tc.variables["CMAKE_SKIP_RPATH"] = True
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        if not os.path.isfile(os.path.join(self.source_folder, "test-dev", "all_tests.txt")):
            raise ConanException("Complete upstream development test inventory is missing from source")
        cmake = CMake(self)
        cmake.configure()
        env = Environment()
        env.prepend_path("LD_LIBRARY_PATH", self.build_folder)
        with env.vars(self).apply():
            cmake.build()
            self.run("ctest --output-on-failure --verbose", cwd=self.build_folder, env="conanrun")

    def package(self):
        CMake(self).install()
        copy(self, "COPYING*", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["xmp"]
        if not self.options.shared and self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs.append("m")
        self.cpp_info.set_property("cmake_file_name", "libxmp")
        self.cpp_info.set_property("cmake_target_name", "libxmp::libxmp")
        self.cpp_info.set_property("pkg_config_name", "libxmp")
