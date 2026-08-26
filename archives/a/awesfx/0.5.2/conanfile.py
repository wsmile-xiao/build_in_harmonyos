from conan import ConanFile
import os
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches
from conan.tools.files import chmod
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AwesfxConan(ConanFile):
    name = "awesfx"
    version = "0.5.2"
    description = "AWE32 Sound Driver utility programs"
    homepage = "https://github.com/tiwai/awesfx"
    license = "GPL-2.0-or-later"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        AutotoolsToolchain(self).generate()

    def build(self):
        apply_conandata_patches(self)
        chmod(self, "configure", permission=0o755)
        build_configure = os.path.join(self.build_folder, "configure")
        if os.path.isfile(build_configure):
            os.chmod(build_configure, os.stat(build_configure).st_mode | 0o111)
        autotools = Autotools(self)
        autotools.configure(args=["--disable-alsa"])
        autotools.make(args=["-j1"])

    def package(self):
        Autotools(self).install(args=["-j1"])

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
