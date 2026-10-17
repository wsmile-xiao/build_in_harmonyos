from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os


class Pkcs11HelperConan(ConanFile):
    name = "pkcs11-helper"
    version = "1.30.0"
    description = "A library that simplifies the interaction with PKCS#11 providers for end-user applications"
    license = "BSD-3-Clause"
    homepage = "https://github.com/OpenSC/pkcs11-helper"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.6.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        env = tc.environment()
        env.define("CC", "clang")
        env.define("CXX", "clang++")
        env.define("TMPDIR", os.path.expanduser("~/tmp"))
        # Pass OpenSSL paths directly to configure via env vars
        openssl = self.dependencies["openssl"]
        openssl_root = openssl.package_folder
        if openssl_root:
            env.define("OPENSSL_CFLAGS", f"-I{openssl_root}/include")
            env.define("OPENSSL_LIBS", f"-L{openssl_root}/lib -lssl -lcrypto")
            env.append("PKG_CONFIG_PATH", os.path.join(openssl_root, "lib", "pkgconfig"))
        tc.generate(env)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1", "-o", "aclocal.m4", "-o", "Makefile.in",
                             "-o", "configure", "-o", "config.h.in"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["pkcs11-helper"]
        self.cpp_info.set_property("pkg_config_name", "libpkcs11-helper-1")
        self.cpp_info.requires = ["openssl::openssl"]
