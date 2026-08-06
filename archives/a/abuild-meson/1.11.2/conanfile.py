import os
import shutil
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, download, load
from conan.tools.layout import basic_layout


class AbuildMesonConan(ConanFile):
    name = "abuild-meson"
    version = "1.11.2"
    description = "Alpine abuild wrapper for reproducible Meson configuration"
    license = "Apache-2.0"
    homepage = "https://gitlab.alpinelinux.org/alpine/aports/-/tree/master/main/meson"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch"

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        source = self.conan_data["sources"][self.version]
        download(
            self,
            source["url"],
            os.path.join(self.source_folder, "abuild-meson"),
            sha256=source["sha256"],
        )
        license_file = self.conan_data["license_file"]
        download(
            self,
            license_file["url"],
            os.path.join(self.source_folder, "COPYING"),
            sha256=license_file["sha256"],
        )

    def build(self):
        script = os.path.join(self.source_folder, "abuild-meson")
        if not load(self, script).startswith("#!/bin/sh"):
            raise ConanInvalidConfiguration("abuild-meson has an unexpected shebang")
        shell = self._configure_shell()
        self.run(f'"{shell}" -n "{script}"')

    @staticmethod
    def _configure_shell():
        candidates = [
            os.environ.get("CONFIG_SHELL"),
            shutil.which("sh"),
            "C:/Program Files/Git/bin/sh.exe",
            "C:/Program Files/Git/usr/bin/sh.exe",
            "E:/Git/bin/sh.exe",
            "E:/Git/usr/bin/sh.exe",
        ]
        for candidate in candidates:
            if candidate and os.path.exists(candidate):
                return candidate.replace("\\", "/")
        raise ConanInvalidConfiguration("A POSIX sh executable is required")

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        copy(self, "abuild-meson", src=self.source_folder, dst=bindir)
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        script = os.path.join(bindir, "abuild-meson")
        os.chmod(
            script,
            os.stat(script).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
