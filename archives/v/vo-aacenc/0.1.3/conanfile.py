from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class VoAacencConan(ConanFile):
    name = "vo-aacenc"
    version = "0.1.3"
    description = "VisualOn AAC encoder library"
    license = "Apache-2.0"
    homepage = "https://opencore-amr.sourceforge.net/"
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os != "OHOS" or self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("vo-aacenc is packaged for OHOS armv8 only")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(["--disable-shared", "--enable-static"])
        # Upstream's 2012 config.sub rejects the newer linux-ohos triplet.
        tc.configure_args.extend(["--build=aarch64-unknown-linux-gnu", "--host=aarch64-unknown-linux-gnu"])
        tc.generate()

    def build(self):
        replace_in_file(self, f"{self.source_folder}/configure", "umask 077", "umask 022")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder, dst=f"{self.package_folder}/licenses")

    def package_info(self):
        self.cpp_info.libs = ["vo-aacenc"]
        self.cpp_info.set_property("cmake_file_name", "vo-aacenc")
        self.cpp_info.set_property("cmake_target_name", "vo-aacenc::vo-aacenc")
        self.cpp_info.set_property("pkg_config_name", "vo-aacenc")
