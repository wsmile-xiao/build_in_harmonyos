from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout, CMakeToolchain
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, copy, rmdir
import os


class LibkqueueConan(ConanFile):
    name = "libkqueue"
    version = "2.6.1"
    license = "BSD-3-Clause"
    url = "https://github.com/mheily/libkqueue"
    homepage = "https://github.com/mheily/libkqueue"
    description = "Userspace implementation of the kqueue event notification mechanism"
    topics = ("kqueue", "event", "notification", "epoll")
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_INSTALL_PREFIX"] = os.path.join(self.package_folder)
        tc.variables["STATIC_KQUEUE"] = not self.options.shared
        # HarmonyOS is not mapped to a versioned CMake platform, so
        # CMAKE_SHARED_LIBRARY_SONAME_<lang>_FLAG stays undefined and the
        # produced libkqueue.so would have no ELF DT_SONAME (CI L5 soname
        # gate fails). Mirror the platform-validated attica/6.14.0 pattern:
        # keep SONAME emission but skip versioned symlinks.
        tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.libs = ["kqueue"]
        self.cpp_info.includedirs = [os.path.join("include", "kqueue")]
        self.cpp_info.system_libs = ["pthread"]
        self.cpp_info.set_property("pkg_config_name", "libkqueue")
