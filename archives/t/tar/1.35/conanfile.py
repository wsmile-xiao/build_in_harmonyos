from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class TarConan(ConanFile):
    name = "tar"
    version = "1.35"
    description = "GNU tape archive utility for creating and extracting archive files"
    license = "GPL-3.0"
    homepage = "https://www.gnu.org/software/tar/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--prefix=")
        tc.configure_args.append("--disable-nls")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j2", "MAKEINFO=true"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["MAKEINFO=true"])

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []