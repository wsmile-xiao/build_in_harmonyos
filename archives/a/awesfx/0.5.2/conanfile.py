from conan import ConanFile
import os
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches
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
        configure_in = os.path.join(self.source_folder, "configure.in")
        with open(configure_in, "r", newline="") as f:
            content = f.read()
        content = content.replace("AM_PATH_ALSA(1.0.0)", "dnl ALSA utilities are unavailable on OHOS")
        with open(configure_in, "w", newline="") as f:
            f.write(content)

        makefile_am = os.path.join(self.source_folder, "Makefile.am")
        with open(makefile_am, "r", newline="") as f:
            content = f.read()
        content = content.replace("sfxload asfxload aweset gusload agusload", "sfxload aweset gusload")
        content = content.replace("asfxload_SOURCES = asfxload.c alsa.c\r\nasfxload_LDADD = awelib/libawe.a @ALSA_LIBS@\r\n\r\n", "")
        content = content.replace("agusload_SOURCES = agusload.c alsa.c\r\nagusload_LDADD = awelib/libawe.a @ALSA_LIBS@\r\n", "")
        with open(makefile_am, "w", newline="") as f:
            f.write(content)

        self.run("autoreconf -fi", cwd=self.source_folder)
        for folder in (self.source_folder, self.build_folder):
            configure = os.path.join(folder, "configure")
            if os.path.isfile(configure):
                os.chmod(configure, 0o755)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        Autotools(self).install(args=["-j1"])

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
