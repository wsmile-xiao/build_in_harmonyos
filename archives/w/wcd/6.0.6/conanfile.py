"""WCD 6.0.6 directory changer for HarmonyOS PC."""

import os
import shlex

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class WcdConan(ConanFile):
    name = "wcd"
    version = "6.0.6"
    description = "Shell-integrated directory changer"
    homepage = "https://wcd.sourceforge.io/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    license = "GPL-2.0-or-later"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "wcd.sh"

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise RuntimeError("This recipe is verified for HarmonyOS PC AArch64 only")
        executables = self.conf.get("tools.build:compiler_executables", default={})
        cc = shlex.quote(executables.get("c", "clang"))
        self.run(
            f"make -j1 CC={cc} EXT= ENABLE_NLS= CURSES= CFLAGS_USER=-O2 wcd",
            cwd=os.path.join(self.source_folder, "src"),
        )

    def package(self):
        copy(self, "wcd", os.path.join(self.source_folder, "src"),
             os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "wcd.sh", self.export_sources_folder,
             os.path.join(self.package_folder, "share", "wcd"), keep_path=False)
        copy(self, "wcd.1", os.path.join(self.source_folder, "src", "man", "man1"),
             os.path.join(self.package_folder, "share", "man", "man1"),
             keep_path=False)
        copy(self, "copying.txt", os.path.join(self.source_folder, "doc"),
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
