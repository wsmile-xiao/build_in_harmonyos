from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, rm
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibburnConan(ConanFile):
    name = "libburn"
    version = "1.5.6"
    description = "Library for reading/writing optical discs (CD, DVD, BD)"
    license = "GPL-2.0-or-later"
    homepage = "https://libburnia-project.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libburn/1.5.6 only supports Linux and OHOS"
            )
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                "libburn/1.5.6 currently supports only OHOS armv8"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33: build() must use Conan Toolchain (AutotoolsToolchain)
        tc = AutotoolsToolchain(self)
        if self.settings.os == "OHOS":
            # AutotoolsToolchain does not inject OHOS build/host triplets;
            # the patched config.guess/config.sub handle linux-ohos.
            tc.configure_args.extend([
                "--build=aarch64-linux-ohos",
                "--host=aarch64-linux-ohos",
            ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        Autotools(self).install()
        rm(self, "*.la", self.package_folder, recursive=True)

    def package_info(self):
        self.cpp_info.libs = ["burn"]
