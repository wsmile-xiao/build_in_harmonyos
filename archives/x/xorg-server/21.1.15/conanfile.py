import os
from conan import ConanFile
from conan.tools.files import get
from conan.tools.layout import basic_layout

class XorgServerConan(ConanFile):
    name = "xorg-server"
    version = "21.1.15"
    description = "X.Org X Server"
    homepage = "https://www.x.org/"
    license = "MIT"
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"][self.version],
            strip_root=True
        )

    def build(self):
        self.run("./configure --prefix=/usr --disable-xorg --disable-dmx --disable-xvfb --disable-xnest --disable-xquartz --disable-xwin")
        self.run("make -j$(nproc)")

    def package(self):
        self.run("make install DESTDIR={}".format(self.package_folder))

    def package_info(self):
        self.cpp_info.libs = ["Xorg"]
