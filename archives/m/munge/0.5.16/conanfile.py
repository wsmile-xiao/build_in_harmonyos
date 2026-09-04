from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, rmdir
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os


class MungeConan(ConanFile):
    name = "munge"
    version = "0.5.16"
    description = "MUNGE (MUNGE Uid 'N Gid Emporium) - authentication service for creating and validating credentials"
    license = "GPL-3.0-or-later", "LGPL-3.0-or-later"
    homepage = "https://github.com/dun/munge"
    topics = ("authentication", "credentials", "security", "HPC")
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
    }
    default_options = {
        "shared": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("openssl/3.0.16")
        self.requires("bzip2/1.0.8")
        self.requires("zlib/1.3.1")

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        else:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        tc.configure_args.append("--disable-suid")
        tc.configure_args.append("--with-crypto-lib=openssl")
        tc.generate()

    def source(self):
        get(self, **self.conan_data["sources"][0], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        for pattern in ["*.la"]:
            for root, _, files in os.walk(self.package_folder):
                for f in files:
                    if f.endswith(".la"):
                        os.unlink(os.path.join(root, f))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.libs = ["munge"]
        self.cpp_info.requires = ["openssl::openssl", "bzip2::bzip2", "zlib::zlib"]
