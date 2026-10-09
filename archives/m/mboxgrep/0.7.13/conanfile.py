"""Native mboxgrep 0.7.13 for HarmonyOS PC."""

import os
import shlex
import shutil
import tempfile

from conan import ConanFile
from conan.tools.files import copy, get, patch
from conan.tools.layout import basic_layout


class MboxgrepConan(ConanFile):
    name = "mboxgrep"
    version = "0.7.13"
    description = "Select email messages matching a regular expression"
    homepage = "https://mboxgrep.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    license = "GPL-2.0-or-later"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*"

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
                "0001-check-only-perl-regex-without-pcre2.patch",
            ),
        )

    def build(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise RuntimeError("This recipe is verified only on HarmonyOS PC AArch64")
        executables = self.conf.get("tools.build:compiler_executables", default={})
        cc = shlex.quote(executables.get("c", "clang"))
        # Autoconf uses shell scratch files. The shared Conan cache is not
        # reliable for those files on this PC, and /tmp is read-only.
        with tempfile.TemporaryDirectory(
            prefix="mboxgrep-build-", dir="/data/storage/el2/base/cache"
        ) as work:
            shutil.copytree(self.source_folder, work, dirs_exist_ok=True)
            quoted_work = shlex.quote(work)
            self.run(
                f"TMPDIR={quoted_work} CC={cc} CFLAGS='-O2' "
                "./configure --without-pcre2 --without-z --prefix=/usr",
                cwd=work,
            )
            self.run("make -j1", cwd=work)
            copy(
                self,
                "mboxgrep",
                os.path.join(work, "src"),
                os.path.join(self.build_folder, "src"),
                keep_path=False,
            )

    def package(self):
        copy(
            self,
            "mboxgrep",
            os.path.join(self.build_folder, "src"),
            os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        copy(
            self,
            "mboxgrep.1",
            os.path.join(self.source_folder, "doc"),
            os.path.join(self.package_folder, "share", "man", "man1"),
            keep_path=False,
        )
        copy(
            self,
            "COPYING.md",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
