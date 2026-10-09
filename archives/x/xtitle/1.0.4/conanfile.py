"""Package Stephen Kinzler's xtitle and xtctl terminal-control scripts."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class XtitleConan(ConanFile):
    name = "xtitle"
    version = "1.0.4"
    description = "Set xterm window title and icon name with shell scripts"
    license = "GPL-2.0-or-later"
    homepage = "https://kinzler.com/me/xtitle"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("xtitle requires a POSIX shell on Linux or OHOS")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        # No compilation: retain the hooks required by conan-verify G1.
        apply_conandata_patches(self)

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        for name in ("xtitle", "xtctl"):
            copy(self, name + ".sh", self.source_folder, bin_dir, keep_path=False)
            os.rename(os.path.join(bin_dir, name + ".sh"), os.path.join(bin_dir, name))
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "xtitle.man", self.source_folder,
             os.path.join(self.package_folder, "share", "man", "man1"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
