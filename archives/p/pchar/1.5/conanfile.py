from conan import ConanFile
from conan.tools.files import get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PcharConan(ConanFile):
    name = "pchar"
    version = "1.5"
    description = "Tool for measuring Internet path characteristics"
    homepage = "https://kitchenlab.org/www/bmah/Software/pchar/"
    license = "BSD-3-Clause"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ValueError("pchar supports Linux and OHOS only")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsToolchain(self).generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure(args=["--disable-suid"])
        autotools.make()

    def package(self):
        Autotools(self).install()

    def package_info(self):
        self.cpp_info.libs = []
