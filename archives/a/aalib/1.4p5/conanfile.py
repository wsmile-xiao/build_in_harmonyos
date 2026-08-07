from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AAlibConan(ConanFile):
    name = "aalib"
    version = "1.4p5"
    description = "Portable ASCII-art graphics library"
    license = "GPL-2.0-or-later"
    homepage = "https://aa-project.sourceforge.net/aalib/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--with-x11-driver=no",
            "--with-slang-driver=no",
            "--with-curses-driver=no",
            "--disable-shared",
            "--enable-static",
        ])

        if self.settings.os == "OHOS":
            if self.settings.arch != "armv8":
                raise ConanInvalidConfiguration(
                    "aalib/1.4p5 currently supports only OHOS armv8"
                )
            # AutotoolsToolchain does not inject OHOS build/host triplets here,
            # while upstream config.sub does not know HarmonyOS uname output.
            # The linux-ohos triplet works together with 0001-config.sub-ohos.patch.
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
        autotools.make(args=["check"])

    def package(self):
        Autotools(self).install()

    def package_info(self):
        self.cpp_info.libs = ["aa"]