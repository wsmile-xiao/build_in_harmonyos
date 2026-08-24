import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMakeDeps, CMakeToolchain
from conan.tools.files import apply_conandata_patches, get, copy
from conan.tools.layout import basic_layout


class AvroCppConan(ConanFile):
    name = "avro-cpp"
    version = "1.12.1"
    package_type = "library"
    description = "Apache Avro C++ serialization library"
    license = "Apache-2.0"
    homepage = "https://avro.apache.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("serialization", "schema", "apache-avro")
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("avro-cpp supports Linux and OHOS only")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("avro-cpp OHOS validation requires armv8")

    def requirements(self):
        self.requires("boost/1.84.0")
        self.requires("zlib/1.3.1")
        self.requires("fmt/8.1.1")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["AVRO_BUILD_STATIC"] = not self.options.shared
        tc.variables["AVRO_BUILD_SHARED"] = bool(self.options.shared)
        tc.variables["AVRO_BUILD_TESTS"] = True
        tc.variables["AVRO_BUILD_EXECUTABLES"] = True
        tc.variables["AVRO_USE_BOOST"] = True
        tc.variables["FETCHCONTENT_FULLY_DISCONNECTED"] = True
        # The OHOS SDK lld depends on libxml2.so.16, which is unavailable in
        # the CI worker runtime. Apply the HNP linker to CMake try-compile,
        # test, and final link commands through the generated toolchain.
        if self.settings.os == "OHOS":
            hnp_ld = "-fuse-ld=/data/service/hnp/bin/ld"
            tc.cache_variables["CMAKE_EXE_LINKER_FLAGS"] = hnp_ld
            tc.cache_variables["CMAKE_SHARED_LINKER_FLAGS"] = hnp_ld
            tc.cache_variables["CMAKE_MODULE_LINKER_FLAGS"] = hnp_ld
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        src_dir = os.path.join(self.source_folder, "lang", "c++")
        build_dir = os.path.join(self.build_folder, "build", "Release")
        os.makedirs(build_dir, exist_ok=True)
        self.run(f'cmake -G "Unix Makefiles" '
                 f'-DCMAKE_TOOLCHAIN_FILE="{os.path.join(self.generators_folder, "conan_toolchain.cmake")}" '
                 f'-DCMAKE_INSTALL_PREFIX="{self.package_folder}" '
                 f'-DCMAKE_BUILD_TYPE="Release" '
                 f'"{src_dir}"',
                 cwd=build_dir)
        self.run(f'cmake --build . -j1 --config Release', cwd=build_dir, env="conanrun")
        self.run(f'ctest --output-on-failure', cwd=build_dir, env="conanrun")

    def package(self):
        build_dir = os.path.join(self.build_folder, "build", "Release")
        self.run(f'cmake --install .', cwd=build_dir)
        copy(self, "LICENSE.txt", src=os.path.join(self.source_folder, "lang", "c++"),
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["avrocpp_s"]
        self.cpp_info.set_property("cmake_file_name", "avrocpp")
        self.cpp_info.set_property("cmake_target_name", "avrocpp_s")
        self.cpp_info.set_property("pkg_config_name", "avro-cpp")
        # avro's public headers (Exception.hh, ...) include <fmt/core.h>,
        # <boost/...>, <zlib.h> directly, so these are transitive.
        self.cpp_info.requires = ["boost::boost", "fmt::fmt", "zlib::zlib"]
