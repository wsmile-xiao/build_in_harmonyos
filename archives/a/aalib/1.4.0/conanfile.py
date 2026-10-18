from conan import ConanFile
from conan.tools.files import get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AAlibConan(ConanFile):
    name = "aalib"
    version = "1.4.0"
    description = "Portable ASCII-art graphics library for C applications"
    homepage = "https://aa-project.sourceforge.net/aalib/"
    license = "LGPL-2.0-or-later"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--disable-shared",
            "--enable-static",
            "--with-x11-driver=no",
            "--with-slang-driver=no",
            "--with-curses-driver=no",
        ])
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        Autotools(self).install()

    def package_info(self):
        self.cpp_info.libs = ["aa"]
