"""WOL 0.7.1 Wake-on-LAN command for HarmonyOS PC."""

import os
import shlex
import shutil
import tempfile

from conan import ConanFile
from conan.tools.files import copy, get, patch, replace_in_file
from conan.tools.layout import basic_layout


class WolConan(ConanFile):
    name = "wol"
    version = "0.7.1"
    description = "Wake-on-LAN Magic Packet sender"
    homepage = "https://sourceforge.net/projects/wake-on-lan/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    license = "GPL-2.0-or-later"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "build_aux/*", "patches/*"

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # The release's 2004 config.sub does not recognize aarch64/OHOS.
        copy(self, "config.sub", os.path.join(self.export_sources_folder, "build_aux"),
             self.source_folder, keep_path=False)
        os.chmod(os.path.join(self.source_folder, "config.sub"), 0o755)
        patch(self, base_path=self.source_folder,
              patch_file=os.path.join(self.export_sources_folder, "patches",
                                      "0001-guard-legacy-getline-prototypes-on-glibc.patch"))
        # configure defines HAVE_ETHER_HOSTTON=0; the upstream header tests
        # definedness instead of value and omits the fallback prototype.
        replace_in_file(self, os.path.join(self.source_folder, "lib", "ether.h"),
                        "#if !defined(HAVE_ETHER_HOSTTON)",
                        "#if !HAVE_ETHER_HOSTTON")

    def build(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise RuntimeError("This recipe is verified for HarmonyOS PC AArch64 only")
        executables = self.conf.get("tools.build:compiler_executables", default={})
        cc = shlex.quote(executables.get("c", "clang"))
        with tempfile.TemporaryDirectory(prefix="wol-build-", dir="/data/storage/el2/base/cache") as work:
            shutil.copytree(self.source_folder, work, dirs_exist_ok=True)
            temp = shlex.quote(work)
            self.run(
                f"TMPDIR={temp} CC={cc} ./configure "
                "--build=aarch64-unknown-ohos --host=aarch64-unknown-ohos "
                "--disable-nls --prefix=/usr",
                cwd=work,
            )
            self.run("make -j1", cwd=work)
            # Upstream check has no test cases; it is a build consistency target.
            self.run("make -j1 check", cwd=work)
            copy(self, "wol*", os.path.join(work, "src"),
                 os.path.join(self.build_folder, "src"), keep_path=False)
            copy(self, "wol.1", os.path.join(work, "doc"),
                 os.path.join(self.build_folder, "doc"), keep_path=False)

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        for program in ("wol", "wol-bootptab", "wol-dhcpdconf"):
            copy(self, program, os.path.join(self.build_folder, "src"),
                 bindir, keep_path=False)
        copy(self, "wol.1", os.path.join(self.build_folder, "doc"),
             os.path.join(self.package_folder, "share", "man", "man1"),
             keep_path=False)
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
