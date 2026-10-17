from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import copy
import os


class GeosConan(ConanFile):
    name = "geos"
    version = "3.13.0"
    description = "GEOS (Geometry Engine, Open Source) is a C++ port of the Java Topology Suite (JTS)"
    license = "LGPL-2.1-or-later"
    homepage = "https://libgeos.org/"
    url = "https://download.osgeo.org/geos/geos-3.13.0.tar.bz2"
    topics = ("geos", "geometry", "gis", "topology", "jts")
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "patches/*"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "build_geosop": [True, False],
        "build_testing": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "build_geosop": True,
        "build_testing": False,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        # R26: system-same-name library must be static to avoid polluting /lib
        # Force static; fPIC option kept for transitive consumers but unused here
        self.options.shared = False

    def layout(self):
        cmake_layout(self)

    def source(self):
        # conandata.yml provides source URL + sha256
        # strip_root=True flattens geos-3.13.0/ to current dir
        from conan.tools.files import get
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        from conan.tools.cmake import CMakeToolchain
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "OFF" if not self.options.shared else "ON"
        tc.variables["BUILD_TESTING"] = "ON" if self.options.build_testing else "OFF"
        # R38: build_geosop option must drive CMake so commands.json matches产物
        tc.variables["BUILD_GEOSOP"] = "ON" if self.options.build_geosop else "OFF"
        tc.variables["BUILD_DOCUMENTATION"] = "OFF"
        tc.variables["BUILD_BENCHMARKS"] = "OFF"
        tc.variables["BUILD_WEBSITE"] = "OFF"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Copy license
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Main C++ library
        # 根 cpp_info 只设置 cmake_file_name；cmake_target_name 由各组件单独声明
        # 避免根与组件同名导致 CMakeDeps 生成 IMPORTED target 名冲突
        self.cpp_info.set_property("cmake_file_name", "geos")

        # geos (C++ API)
        self.cpp_info.components["geos"].libs = ["geos"]
        self.cpp_info.components["geos"].set_property("cmake_target_name", "GEOS::geos")

        # geos_c (C API, depends on geos)
        self.cpp_info.components["geos_c"].libs = ["geos_c"]
        self.cpp_info.components["geos_c"].requires = ["geos"]
        self.cpp_info.components["geos_c"].set_property("cmake_target_name", "GEOS::geos_c")

        # R38: command-line tool geosop lives in bin/
        # (No cpp_info needed for executables)
