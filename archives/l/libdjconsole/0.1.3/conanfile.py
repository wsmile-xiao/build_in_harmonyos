import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LibdjconsoleConan(ConanFile):
    name = "libdjconsole"
    version = "0.1.3"
    description = "C++ library for Hercules DJ Console devices"
    license = "GPL-2.0-or-later"
    homepage = "https://djplay.sourceforge.net/"
    url = "https://sourceforge.net/projects/djplay/files/libdjconsole/0.1.3/"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("libusb-compat/0.1.7")

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        self._write_cmake_project()

    def _write_cmake_project(self):
        cmake_lists = r'''cmake_minimum_required(VERSION 3.15)
project(libdjconsole VERSION 0.1.3 LANGUAGES CXX)

include(GNUInstallDirs)
find_package(Threads REQUIRED)
find_package(libusb-compat CONFIG REQUIRED)

add_library(djconsole bitfield.cpp delta.cpp djconsole.cpp)
add_library(libdjconsole::libdjconsole ALIAS djconsole)
set_target_properties(djconsole PROPERTIES OUTPUT_NAME djconsole)
target_compile_features(djconsole PUBLIC cxx_std_11)
target_include_directories(djconsole PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
    $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>)
target_compile_definitions(djconsole PRIVATE
    DATADIR="${CMAKE_INSTALL_PREFIX}/${CMAKE_INSTALL_DATADIR}/libdjconsole")
target_link_libraries(djconsole PUBLIC libusb-compat::libusb-compat Threads::Threads)

install(TARGETS djconsole EXPORT libdjconsoleTargets
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})
install(FILES djconsole.h delta.h bitfield.h
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
install(DIRECTORY DESTINATION ${CMAKE_INSTALL_DATADIR}/libdjconsole)
install(FILES
    06f8-b000.buttons 06f8-b000.leds 06f8-b000.mouse
    06f8-b100.buttons 06f8-b100.leds 06f8-b100.mouse
    06f8-b101.buttons
    06f8-d001.buttons 06f8-d001.leds 06f8-d001.mouse
    DESTINATION ${CMAKE_INSTALL_DATADIR}/libdjconsole)
install(FILES 45-hpdjconsole.rules
    DESTINATION ${CMAKE_INSTALL_SYSCONFDIR}/udev/rules.d)
'''
        path = os.path.join(self.source_folder, "CMakeLists.txt")
        with open(path, "w", encoding="utf-8", newline="\n") as cmake_file:
            cmake_file.write(cmake_lists)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        CMake(self).install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["djconsole"]
        self.cpp_info.requires = ["libusb-compat::libusb-compat"]
        self.cpp_info.set_property("cmake_file_name", "libdjconsole")
        self.cpp_info.set_property("cmake_target_name", "libdjconsole::libdjconsole")
