import os
from conan import ConanFile
from conan.tools.files import get
from conan.tools.layout import basic_layout

class LibkcapiConan(ConanFile):
    name = "libkcapi"
    version = "1.5.0"
    description = "User-space interface to the Linux kernel Crypto API"
    homepage = "https://www.chronox.de/libkcapi/"
    license = "BSD-3-Clause OR GPL-2.0-only"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        self.run("./configure --prefix=/usr --disable-shared --enable-static")
        self.run("make -j$(nproc)")

    def package(self):
        self.run(f"make install DESTDIR={self.package_folder}")

    def package_info(self):
        self.cpp_info.libs = ["kcapi"]
