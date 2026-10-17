#!/usr/bin/env python3
"""Conan recipe for diaspora-installer 0.9.0.0-debian2-nmu1 — pure shell/config bundle.

diaspora-installer is the Debian packaging of the diaspora* pod set-up helper
(social networking service installer). It contains POSIX shell scripts and
configuration templates (nginx, database.yml, diaspora.toml...) that download
and configure the diaspora* software on a server. There is no binary to build
(the upstream README states "There's no binary to be built.").

Platform adaptations for OHOS:
  1. No compiler needed — pure shell/configuration data, no build system.
  2. The packaged scripts and config templates are installed under
     share/diaspora-installer/, matching the upstream layout relativized.
  3. diaspora-versions.sh is a self-contained, side-effect free version
     helper (it only exports version variables); it is exposed on PATH so
     consumers can source staging scripts.
  4. The remaining scripts (grantpriv/adduser/initdb/...) depend on Debian
     runtime hosts (psql, adduser, /etc/diaspora) — they are shipped but not
     executed by the test.

R28: test_package/ exists.
R34: test_package runs diaspora-versions.sh with real sh and asserts the
     embedded version (0.9.0.0) plus shell syntax of all shipped .sh files.
R38: commands.json declared at software level (tool-type package).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches
from conan.tools.layout import basic_layout


class DiasporaInstallerConan(ConanFile):
    name = "diaspora-installer"
    version = "0.9.0.0-debian2-nmu1"
    description = "Distributed social networking service - installer scripts"
    license = "GPL-2.0-or-later"
    homepage = "https://wiki.debian.org/Diaspora"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    # OHOS profile requires four settings (L0p gate)
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def package(self):
        src = self.source_folder
        dst = os.path.join(self.package_folder, "share", "diaspora-installer")
        # Shell scripts
        copy(self, "*.sh", src=src, dst=dst)
        # Config templates and docs
        for fname in ("diaspora-common.conf", "diaspora.toml",
                      "diaspora.example.conf", "nginx.conf.example",
                      "nginx.conf.nohttps.example", "database.yml",
                      "README", "sha256sums"):
            copy(self, fname, src=src,
                 dst=dst, keep_path=False)
        # License (GPL-2+)
        copy(self, "debian/copyright", src=src,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        share_dir = os.path.join(self.package_folder, "share", "diaspora-installer")
        if os.path.isdir(share_dir):
            self.runenv_info.append_path("PATH", share_dir)
            self.buildenv_info.append_path("PATH", share_dir)
            self.runenv_info.define("DIASPORA_INSTALLER_DIR", share_dir)