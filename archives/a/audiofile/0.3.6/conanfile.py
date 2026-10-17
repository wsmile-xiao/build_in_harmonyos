from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AudiofileConan(ConanFile):
    name = "audiofile"
    version = "0.3.6"
    package_type = "library"
    description = "Library for reading and writing audio files"
    license = "LGPL-2.0-only, GPL-2.0-only"
    homepage = "https://audiofile.68k.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("audio", "wav", "aiff")

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"audiofile is adapted for Linux/OHOS, got {self.settings.os}"
            )
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                f"audiofile/0.3.6 is validated for OHOS armv8, got {self.settings.arch}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # FLAC would add a transitive dependency that this recipe does not
        # package. Keep the base audio formats and their upstream tests enabled.
        tc.configure_args.extend(["--disable-flac", "--disable-docs", "--disable-examples"])
        # sfcommands mix C and C++ (AudioFormat.cpp); on OHOS with libc++
        # the C linker driver omits -lc++, so add it explicitly.
        tc.extra_ldflags.append("-lc++")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        # Exercise the upstream non-FLAC test suite; do not treat a successful
        # library build as a substitute for its functional tests.
        autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING*", src=self.source_folder, dst=f"{self.package_folder}/licenses")

    def package_info(self):
        self.cpp_info.libs = ["audiofile"]
        self.cpp_info.set_property("cmake_file_name", "audiofile")
        self.cpp_info.set_property("cmake_target_name", "audiofile::audiofile")
        self.cpp_info.set_property("pkg_config_name", "audiofile")
