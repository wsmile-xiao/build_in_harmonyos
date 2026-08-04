from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import get, copy
import os


class LibrttopoConan(ConanFile):
    name = "librttopo"
    version = "1.1.0"
    description = "RT Topology Library - ISO SQL/MM (13249) topologies API, derived from PostGIS liblwgeom"
    license = "GPL-2.0-or-later"
    homepage = "https://gitlab.com/rttopo/librttopo"
    url = "https://sources.voidlinux.org/librttopo-1.1.0/librttopo-1.1.0.tar.gz"
    topics = ("librttopo", "topology", "gis", "postgis", "geometry", "sql-mm")
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "patches/*"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires("geos/3.13.0")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        cmake_src = os.path.join(self.export_sources_folder, "patches", "CMakeLists.txt")
        if os.path.isfile(cmake_src):
            copy(self, "CMakeLists.txt", src=os.path.dirname(cmake_src), dst=self.source_folder)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.generate()
        # Generate CMakeDeps files for geos dependency so find_package(geos CONFIG) works
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "rttopo")
        self.cpp_info.set_property("cmake_target_name", "rttopo::rttopo")
        self.cpp_info.libs = ["rttopo"]
        self.cpp_info.system_libs = ["m"]
