from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout
import os


class AcpiOverrideConan(ConanFile):
    name = "acpi-override"
    version = "0.1+nmu2"
    package_type = "application"
    description = "initramfs-tools hook to override ACPI tables"
    license = "GPL-2.0-or-later"
    homepage = "https://salsa.debian.org/debian/acpi-override"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("acpi-override requires Linux or OHOS")
        if str(self.settings.arch) not in ("armv8", "aarch64"):
            raise ConanInvalidConfiguration("acpi-override supports only armv8/aarch64")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # This Debian-native source is a shell hook; apply portability patches
        # without introducing a C/C++ build step.
        apply_conandata_patches(self)

    def package(self):
        copy(self, "acpi-override", self.source_folder, os.path.join(self.package_folder, "share", "initramfs-tools", "hooks"))
        os.makedirs(os.path.join(self.package_folder, "var", "lib", "acpi-override"), exist_ok=True)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.buildenv_info.define_path("ACPI_OVERRIDE_HOOK", os.path.join(self.package_folder, "share", "initramfs-tools", "hooks", "acpi-override"))
