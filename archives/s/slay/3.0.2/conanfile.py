#!/usr/bin/env python3
"""slay 3.0.2: install the upstream POSIX shell CLI without Debian maintainer scripts."""
import os

from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches


class SlayConan(ConanFile):
    name = "slay"
    version = "3.0.2"
    description = "Kill all processes belonging to a specified user"
    license = "GPL-2.0-only"
    homepage = "https://salsa.debian.org/debian/slay"
    url = "https://salsa.debian.org/debian/slay"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "GPL-2.0.txt", self.recipe_folder, self.export_sources_folder)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)  # No patches or compilation for this release.

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        src = os.path.join(self.source_folder, "slay")
        dst = os.path.join(bin_dir, "slay")
        with open(src, "r", encoding="utf-8") as stream:
            script = stream.read()
        if self.settings.os == "OHOS":
            # E165: OHOS sh is /system/bin/sh; the upstream Linux PATH omits it.
            script = script.replace("#!/bin/sh\n", "#!/system/bin/sh\n", 1)
            script = script.replace("PATH=/usr/sbin:/sbin:/usr/bin:/bin\n",
                                    "PATH=/system/bin:/data/service/hnp/bin:/usr/sbin:/sbin:/usr/bin:/bin\n", 1)
        with open(dst, "w", encoding="utf-8") as stream:
            stream.write(script)
        os.chmod(dst, 0o755)
        copy(self, "slay.8", self.source_folder,
             os.path.join(self.package_folder, "share", "man", "man8"), keep_path=False)
        copy(self, "copyright", os.path.join(self.source_folder, "debian"),
             os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "GPL-2.0.txt", self.export_sources_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
