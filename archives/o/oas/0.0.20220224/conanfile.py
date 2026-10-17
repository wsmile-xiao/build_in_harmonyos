import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, get


class OasConan(ConanFile):
    """oas (Output Address Selection) -- a connect() interposer shared library.

    Upstream ships autotools inputs only (configure.ac + Makefile.am, no
    configure/Makefile.in). This host's automake/aclocal/libtoolize exist under
    ~/usr/local/bin but are not executable: their shebang interpreter is missing,
    and running them through the real perl fails with "Can't locate
    Automake/Config.pm" (the E116 signature). A real "autoreconf -fi" run
    therefore returns rc=2 and generates none of the six required files, so the
    recipe builds the single upstream target (src/Makefile.am:
    lib_LTLIBRARIES = liboas.la, AM_LDFLAGS = -ldl) through an injected
    CMakeLists.txt. See notes.md section 1 for the measured evidence.
    """

    name = "oas"
    version = "0.0.20220224"
    description = ("Output Address Selection: shared library wrapping connect() "
                   "to steer IPv6 source address selection from a rule list")
    license = "MIT"
    homepage = "https://github.com/ThomasNoll/oas"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("ipv6", "connect", "ld-preload", "rtld-next", "network")
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "CMakeLists.txt", "patches/*"

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        copy(self, "CMakeLists.txt", self.export_sources_folder, self.source_folder)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "oas")
        self.cpp_info.set_property("cmake_target_name", "oas::oas")
        self.cpp_info.libs = ["oas"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = ["lib"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl"]
