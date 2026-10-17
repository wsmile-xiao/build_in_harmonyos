"""Build the metacam 1.2 command-line tool for HarmonyOS PC."""

import os
import shlex
import shutil
import tempfile

from conan import ConanFile
from conan.tools.files import copy, get, replace_in_file
from conan.tools.layout import basic_layout


class MetacamConan(ConanFile):
    name = "metacam"
    version = "1.2"
    description = "Extract EXIF metadata from camera images"
    homepage = "https://packages.debian.org/source/metacam"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    license = "GPL-2.0-or-later"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        replace_in_file(self, os.path.join(self.source_folder, "metacam.cc"),
                        "bool found_exif = true;", "bool found_exif = false;")
        replace_in_file(self, os.path.join(self.source_folder, "metacam.cc"),
                        "is.clear(is.rdstate() & (~ios::eofbit));",
                        "is.clear();")

    def build(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise RuntimeError("This recipe requires HarmonyOS PC AArch64 validation")
        executables = self.conf.get("tools.build:compiler_executables", default={})
        cxx = shlex.quote(executables.get("cpp", "clang++"))
        # Make emits dependency files and objects into the source directory.
        # Build in app-private writable storage, away from the shared cache.
        with tempfile.TemporaryDirectory(
            prefix="metacam-build-", dir="/data/storage/el2/base/cache"
        ) as work:
            shutil.copytree(self.source_folder, work, dirs_exist_ok=True)
            self.run(f"make -j1 CXX={cxx}", cwd=work)
            copy(
                self,
                "metacam",
                work,
                os.path.join(self.build_folder, "bin"),
                keep_path=False,
            )

    def package(self):
        copy(
            self,
            "metacam",
            os.path.join(self.build_folder, "bin"),
            os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        copy(
            self,
            "LICENSE.TXT",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
