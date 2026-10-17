#!/usr/bin/env python3
"""Conan recipe for defaultbrowser 1.1 — macOS-only CLI tool.

This package is macOS-specific (uses Foundation/ApplicationServices framework).
Cannot be compiled on OpenHarmony, so the package preserves upstream sources and
installs a placeholder command with a clear diagnostic.
"""
from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save
import os


class DefaultbrowserConan(ConanFile):
    name = "defaultbrowser"
    version = "1.1"
    description = "Command-line tool for getting and setting the default browser on macOS"
    license = "MIT"
    homepage = "https://github.com/kerma/defaultbrowser"
    url = "https://github.com/kerma/defaultbrowser/archive/refs/tags/1.1.tar.gz"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        self.output.info("defaultbrowser is macOS-only (uses Foundation/ApplicationServices)")
        self.output.info("Skipping build: not applicable for OpenHarmony")

    def package(self):
        copy(self, "*", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "defaultbrowser"))
        bin_dir = os.path.join(self.package_folder, "bin")
        save(
            self,
            os.path.join(bin_dir, "defaultbrowser"),
            "#!/usr/bin/env bash\n"
            'echo "defaultbrowser is macOS-only: not available on OpenHarmony"\n'
            "exit 1\n",
        )
        os.chmod(os.path.join(bin_dir, "defaultbrowser"), 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
