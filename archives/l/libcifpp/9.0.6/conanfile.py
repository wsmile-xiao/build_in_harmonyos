from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.gnu import PkgConfigDeps
from conan.tools.files import apply_conandata_patches, export_conandata_patches, copy, get
import os

class LibcifppConan(ConanFile):
    name = "libcifpp"
    version = "9.0.6"
    description = "A C++ library for reading and writing CIF (Crystallographic Information File) data"
    license = "BSD-2-Clause"
    homepage = "https://github.com/PDB-REDO/libcifpp"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("cif", "crystallography", "pdb", "mmcif")

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")
        self.requires("eigen/3.4.0")
        self.requires("pcre2/10.45.1")
        self.requires("fast_float/7.0.0")
        self.requires("fmt/8.1.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # OHOS: std::from_chars for float is not available, use fast_float
        # CMakeLists.txt try_compile detects this automatically
        tc.variables["CIFPP_DOWNLOAD_CCD"] = False
        tc.variables["CIFPP_INSTALL_UPDATE_SCRIPT"] = False
        tc.variables["BUILD_TESTING"] = False
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

        # PkgConfigDeps for pcre2 (CMakeLists.txt uses pkg_check_modules for pcre2)
        pkg = PkgConfigDeps(self)
        pkg.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

        # Copy data files (dictionaries) to package
        copy(self, "*.dic", dst=os.path.join(self.package_folder, "share", "libcifpp"),
             src=os.path.join(self.source_folder, "rsrc"))

    def package_info(self):
        self.cpp_info.libs = ["cifpp"]
        self.cpp_info.set_property("cmake_file_name", "cifpp")
        self.cpp_info.set_property("cmake_target_name", "cifpp::cifpp")

        # Data directory for dictionary files
        self.cpp_info.defines.append(f'DATA_DIR="{os.path.join(self.package_folder, "share", "libcifpp")}"')

        # Dependencies are transitively linked
        self.cpp_info.requires = ["zlib::zlib", "fmt::fmt", "fast_float::fast_float"]
        # eigen is header-only (build-time only), pcre2 is private but must be declared
        self.cpp_info.requires.append("eigen::eigen")
        self.cpp_info.requires.append("pcre2::pcre2-8")
