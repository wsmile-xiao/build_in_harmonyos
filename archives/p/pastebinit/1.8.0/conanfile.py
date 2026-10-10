#!/usr/bin/env python3
"""Conan recipe for pastebinit 1.8.0 — command-line pastebin client.

pastebinit is a pure Python3 script that sends text to pastebin services.
It optionally uses the 'distro' module to detect the OS and set a default
pastebin. Build step compiles .po translation files to .mo via msgfmt.
"""

import os
import shutil
import glob

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class PastebinitConan(ConanFile):
    name = "pastebinit"
    version = "1.8.0"
    package_type = "application"
    license = "GPL-2.0+"
    homepage = "https://launchpad.net/pastebinit"
    description = "command-line pastebin client (pure Python3)"

    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("distro/1.9.0")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # Compile .po translation files to .mo using msgfmt
        po_files = glob.glob(os.path.join(self.source_folder, "*.po"))
        for po in po_files:
            lang = os.path.splitext(os.path.basename(po))[0]
            mo_dir = os.path.join(self.build_folder, "mo", lang, "LC_MESSAGES")
            os.makedirs(mo_dir, exist_ok=True)
            mo_path = os.path.join(mo_dir, "pastebinit.mo")
            self.run(f'msgfmt "{po}" -o "{mo_path}"')

        # Run upstream integration test (test.sh)
        # Patches test.sh for OHOS: python->python3, wget->curl
        self.run('sh test.sh', cwd=self.source_folder)

    def package(self):
        # Install pastebinit script to bin/
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        shutil.copy2(
            os.path.join(self.source_folder, "pastebinit"),
            os.path.join(bindir, "pastebinit"),
        )
        os.chmod(os.path.join(bindir, "pastebinit"), 0o755)

        # Install utils (pbget, pbput, pbputs)
        utils_dir = os.path.join(self.source_folder, "utils")
        if os.path.isdir(utils_dir):
            for name in ("pbget", "pbput", "pbputs"):
                src = os.path.join(utils_dir, name)
                if os.path.isfile(src):
                    shutil.copy2(src, os.path.join(bindir, name))
                    os.chmod(os.path.join(bindir, name), 0o755)

        # Install pastebin.d config files
        conf_src = os.path.join(self.source_folder, "pastebin.d")
        if os.path.isdir(conf_src):
            conf_dst = os.path.join(
                self.package_folder, "share", "pastebinit", "pastebin.d"
            )
            shutil.copytree(conf_src, conf_dst)

        # Install compiled .mo translation files
        mo_root = os.path.join(self.build_folder, "mo")
        if os.path.isdir(mo_root):
            locale_dst = os.path.join(self.package_folder, "share", "locale")
            for lang_dir in os.listdir(mo_root):
                src_mo = os.path.join(
                    mo_root, lang_dir, "LC_MESSAGES", "pastebinit.mo"
                )
                if os.path.isfile(src_mo):
                    dst_dir = os.path.join(
                        locale_dst, lang_dir, "LC_MESSAGES"
                    )
                    os.makedirs(dst_dir, exist_ok=True)
                    shutil.copy2(src_mo, os.path.join(dst_dir, "pastebinit.mo"))

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
