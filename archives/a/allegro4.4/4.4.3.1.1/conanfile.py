import os
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, replace_in_file


class Allegro44Conan(ConanFile):
    name = "allegro4.4"
    version = "4.4.3.1.1"
    description = "Allegro 4 — A cross-platform game programming library"
    license = "BSD-3-Clause"
    url = "https://github.com/liballeg/allegro5"
    homepage = "https://liballeg.org/"
    topics = ("game", "multimedia", "graphics", "audio")
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }
    package_type = "library"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS", "Windows"):
            raise ConanInvalidConfiguration(
                f"allegro4.4 supports Linux, OHOS, and Windows, not {self.settings.os}"
            )

    def source(self):
        get(
            self,
            **self.conan_data["sources"][self.version],
            strip_root=True,
        )
        # Fix cmake_minimum_required for modern CMake compatibility
        cmake_file = os.path.join(self.source_folder, "CMakeLists.txt")
        replace_in_file(
            self,
            cmake_file,
            "cmake_minimum_required(VERSION 2.6 FATAL_ERROR)",
            "cmake_minimum_required(VERSION 3.5)",
        )
        # Strip addons from PKG_CONFIG_FILES (not available on OHOS)
        replace_in_file(
            self,
            cmake_file,
            'set(PKG_CONFIG_FILES\n    allegro\n    allegrogl\n    jpgalleg\n    loadpng\n    logg\n    )',
            'set(PKG_CONFIG_FILES\n    allegro\n    )',
        )

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["SHARED"] = self.options.shared
        tc.variables["WANT_X11"] = False
        tc.variables["WANT_ALSA"] = False
        tc.variables["WANT_OSS"] = False
        tc.variables["WANT_JACK"] = False
        tc.variables["WANT_SGIAUDIO"] = False
        tc.variables["WANT_LINUX_CONSOLE"] = False
        tc.variables["WANT_MODULES"] = False
        tc.variables["WANT_FRAMEWORKS"] = False
        tc.variables["WANT_EMBED"] = False
        tc.variables["WANT_MAGIC_MAIN"] = False
        tc.variables["WANT_ALLEGROGL"] = False
        tc.variables["WANT_LOADPNG"] = False
        tc.variables["WANT_LOGG"] = False
        tc.variables["WANT_JPGALLEG"] = False
        tc.variables["WANT_TESTS"] = False
        tc.variables["WANT_EXAMPLES"] = False
        tc.variables["WANT_TOOLS"] = False
        if str(self.settings.os) == "OHOS":
            # OHOS: CMake may not set UNIX automatically for HarmonyOS
            tc.variables["UNIX"] = "TRUE"
            # OHOS/musl: librt is built into libc, no separate -lrt needed
            tc.variables["RT_LIBRARY"] = ""
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "license.txt", src=os.path.join(self.source_folder, "docs", "txt"),
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "allegro4.4")
        self.cpp_info.set_property("cmake_target_name", "allegro4.4::allegro")
        self.cpp_info.set_property("pkg_config_name", "allegro")
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.libs = ["alleg"]
        else:
            self.cpp_info.libs = ["alleg44"]
        if str(self.settings.os) == "OHOS":
            self.cpp_info.system_libs = ["m"]
        elif str(self.settings.os) == "Windows":
            self.cpp_info.system_libs = ["m"]
        else:
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
