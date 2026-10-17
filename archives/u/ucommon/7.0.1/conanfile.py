from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, replace_in_file
from conan.tools.gnu import PkgConfigDeps
import os


class UcommonConan(ConanFile):
    name = "ucommon"
    version = "7.0.1"
    description = "GNU uCommon C++ - portable C++ threading and socket abstraction library"
    license = "LGPL-2.1-or-later"
    url = "https://www.gnu.org/software/commoncpp/"
    homepage = "https://packages.debian.org/source/sid/ucommon"
    topics = ("threading", "socket", "abstraction", "gnu")
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_ssl": ["gnutls", "openssl", False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_ssl": "gnutls",
    }
    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        if self.options.with_ssl == "gnutls":
            self.requires("gnutls/3.8.10")
        elif self.options.with_ssl == "openssl":
            self.requires("openssl/3.5.6")

    def build_requirements(self):
        # cmake is provided by the system (4.1.2 on device)
        self.tool_requires("pkgconf/3.0.5")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        # Fix nossl backend function signatures to match header declarations
        secure_cpp = os.path.join(self.source_folder, "nossl", "secure.cpp")
        replace_in_file(self, secure_cpp,
            "secure::server_t secure::server(const char *cert, const char *key)",
            "secure::server_t secure::server(const char *keyfile, const char *authority)")
        replace_in_file(self, secure_cpp,
            "secure::client_t secure::client(const char *ca)",
            "secure::client_t secure::client(const char *authority, const char *paths)")
        
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def generate(self):
        # The upstream CMake file discovers GnuTLS/OpenSSL through pkg-config.
        # PkgConfigDeps creates metadata for Conan dependencies, but CMake's
        # pkg_check_modules() does not search the generators directory unless
        # it is explicitly added to PKG_CONFIG_PATH.
        PkgConfigDeps(self).generate()
        generated_pkgconfig = str(self.generators_folder)
        existing_pkgconfig = os.environ.get("PKG_CONFIG_PATH", "")
        os.environ["PKG_CONFIG_PATH"] = os.pathsep.join(
            path for path in (generated_pkgconfig, existing_pkgconfig) if path
        )

        tc = CMakeToolchain(self)
        tc.variables["BUILD_STDLIB"] = True
        tc.variables["BUILD_STATIC"] = not self.options.shared
        tc.variables["BUILD_TESTING"] = False
        tc.variables["BUILD_EXTRAS"] = False
        tc.variables["CRYPTO_OPENSSL"] = self.options.with_ssl == "openssl"
        if self.options.with_ssl == "gnutls":
            tc.variables["CRYPTO_OPENSSL"] = False
        tc.generate()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # The upstream CMake install produces these three libraries:
        # libcommoncpp, libusecure, and libucommon.  Keep dependency order for
        # static consumers: the compatibility and secure layers use ucommon.
        self.cpp_info.libs = ["commoncpp", "usecure", "ucommon"]
        self.cpp_info.set_property("cmake_file_name", "ucommon")
        self.cpp_info.set_property("cmake_target_name", "ucommon::ucommon")
        self.cpp_info.set_property("pkg_config_name", "ucommon")
        if str(self.settings.os) in ("Linux", "OHOS", "FreeBSD"):
            self.cpp_info.system_libs = ["pthread"]
        if self.options.with_ssl == "gnutls":
            # gnutls/3.8.10 is packaged with shared libraries but does not
            # export its lib directory through runenv_info on OHOS.  Without
            # this path, the device loader may select an incompatible system
            # libgnutls.so.30 instead of the Conan dependency.
            gnutls = self.dependencies.get("gnutls")
            if gnutls:
                for libdir in gnutls.cpp_info.libdirs:
                    self.runenv_info.prepend_path("LD_LIBRARY_PATH", libdir)
