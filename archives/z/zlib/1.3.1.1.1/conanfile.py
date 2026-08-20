from conan import ConanFile
from conan.tools.files import get
import os


class ZlibConan(ConanFile):
    name = "zlib"
    version = "1.3.1.1.1"
    package_type = "library"
    license = "Zlib"
    homepage = "https://zlib.net/"
    description = "General-purpose lossless data-compression library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        prefix = os.path.join(self.build_folder, "stage")
        configure = "./configure" if self.settings.os != "Windows" else "sh configure"
        shared = "--shared" if self.options.shared else "--static"
        cc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("c", "clang")
        self.run(f'CFLAGS="-fPIC -O2" CC="{cc}" {configure} {shared} --prefix="{prefix}"')
        self.run("make -j1")
        self.run("make check")
        self.run(f'make install DESTDIR="{self.package_folder}"')

    def package_info(self):
        self.cpp_info.libs = ["z"]
