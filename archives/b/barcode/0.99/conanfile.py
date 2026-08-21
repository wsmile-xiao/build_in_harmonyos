from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

import os
import stat


class BarcodeConan(ConanFile):
    name = "barcode"
    version = "0.99"
    package_type = "application"
    description = "GNU Barcode command-line generator"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/barcode/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("barcode", "svg", "ean", "upc")

    settings = "os", "arch", "compiler", "build_type"

    exports_sources = "patches/*"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"barcode is adapted for Linux/OHOS, got {self.settings.os}"
            )
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                f"barcode/0.99 is validated for OHOS armv8, got {self.settings.arch}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.settings.os == "OHOS":
            # The bundled 2013 config scripts predate HarmonyOS. The compiler
            # still targets OHOS; these portable triplets only avoid an OS-name
            # rejection in configure's feature detection.
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
            # barcode.h uses #include <gettext.h>; the bundled copy lives in
            # lib/. Add the absolute path so clang finds it regardless of the
            # working directory (the relative -Ilib in Makefile.am resolves
            # against build-release, where lib/ does not exist).
            tc.extra_cflags.append(f"-I{self.source_folder}/lib")
            # clang 15 defaults to -fno-common; barcode 0.99 (2013) relies on
            # tentative definitions of globals like 'streaming' across multiple
            # translation units, which -fno-common turns into duplicate symbols.
            tc.extra_cflags.append("-fcommon")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # HMDFS strips the executable bit on copy; restore it so
        # Autotools.configure() can run ./configure.
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure_path):
            current_mode = os.stat(configure_path).st_mode
            os.chmod(configure_path, current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder, dst=f"{self.package_folder}/licenses")

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
