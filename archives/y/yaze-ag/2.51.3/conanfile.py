"""Native YAZE-AG 2.51.3 application for HarmonyOS PC."""

import os
import shlex

from conan import ConanFile
from conan.tools.files import copy, get, patch
from conan.tools.layout import basic_layout


class YazeAgConan(ConanFile):
    name = "yaze-ag"
    version = "2.51.3"
    description = "Yet Another Z80 Emulator by AG"
    homepage = "https://agl.yaze-ag.de/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    license = "GPL-2.0-or-later"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*", "yaze"

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        patch(
            self,
            base_path=self.source_folder,
            patch_file=os.path.join(
                self.export_sources_folder,
                "patches",
                "0001-use-portable-stat-file-type-predicates.patch",
            ),
        )

    def build(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise RuntimeError("This recipe is verified for HarmonyOS PC AArch64 only")
        executables = self.conf.get("tools.build:compiler_executables", default={})
        cc = shlex.quote(executables.get("c", "clang"))
        libdir = shlex.quote(os.path.join(self.package_folder, "res") + os.sep)
        label = shlex.quote('" (HarmonyOS PC AArch64)"')
        self.run(
            "make -f Makefile_Raspberry_Pi_3_Model_B_ARMv8_64Bit -j1 "
            f"CC={cc} OPTIMIZE=-O2 LIBDIR={libdir} BUILD={label} all",
            cwd=self.source_folder,
        )

    def package(self):
        for binary in ("yaze_bin", "cdm"):
            copy(self, binary, self.source_folder,
                 os.path.join(self.package_folder, "bin"), keep_path=False)
        wrapper = os.path.join(self.package_folder, "bin", "yaze")
        copy(self, "yaze", self.export_sources_folder,
             os.path.join(self.package_folder, "bin"), keep_path=False)
        os.chmod(wrapper, 0o755)
        for pattern in ("*.boot", "*.ktt"):
            copy(self, pattern, self.source_folder,
                 os.path.join(self.package_folder, "res"), keep_path=False)
        for disk in ("BOOT_UTILS.ydsk", "CPM3_SYS.ydsk"):
            copy(self, disk, self.source_folder,
                 os.path.join(self.package_folder, "res", "disks"),
                 keep_path=False)
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
