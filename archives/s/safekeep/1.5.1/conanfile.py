import base64
import os
import stat

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, check_sha256, copy, export_conandata_patches, get, unzip
from conan.tools.layout import basic_layout


class SafekeepConan(ConanFile):
    name = "safekeep"
    version = "1.5.1"
    description = "Python backup manager for centrally orchestrated rdiff-backup jobs"
    license = "GPL-2.0-or-later"
    homepage = "http://safekeep.sourceforge.net/"
    url = "https://github.com/dimipaun/safekeep"
    topics = ("backup", "python", "rdiff-backup", "ssh")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "safekeep-1.5.1.tar.gz.b64", "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        local_archive = os.path.join(self.source_folder, self.conan_data["sources"]["filename"])
        local_archive_b64 = local_archive + ".b64"
        if os.path.isfile(local_archive_b64):
            self.output.info("Using exported safekeep source archive")
            with open(local_archive_b64, "rb") as handle:
                archive_data = base64.b64decode(handle.read())
            with open(local_archive, "wb") as handle:
                handle.write(archive_data)
            check_sha256(self, local_archive, self.conan_data["sources"]["sha256"])
            unzip(self, local_archive, strip_root=True)
            apply_conandata_patches(self)
            return
        if os.path.isfile(local_archive):
            self.output.info("Using exported safekeep source archive")
            check_sha256(self, local_archive, self.conan_data["sources"]["sha256"])
            unzip(self, local_archive, strip_root=True)
            apply_conandata_patches(self)
            return
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        script = os.path.join(self.source_folder, "safekeep")
        with open(script, encoding="utf-8") as handle:
            compile(handle.read(), script, "exec")

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        share_dir = os.path.join(self.package_folder, "share", self.name)
        license_dir = os.path.join(self.package_folder, "licenses")

        copy(self, "safekeep", src=self.source_folder, dst=bin_dir, keep_path=False)
        copy(self, "safekeep-test", src=self.source_folder, dst=share_dir, keep_path=False)
        copy(self, "safekeep.conf", src=self.source_folder, dst=share_dir, keep_path=False)
        copy(self, "safekeep.cron", src=self.source_folder, dst=share_dir, keep_path=False)
        copy(self, "README*", src=self.source_folder, dst=share_dir, keep_path=False)
        copy(self, "INSTALL", src=self.source_folder, dst=share_dir, keep_path=False)
        copy(self, "AUTHORS", src=self.source_folder, dst=share_dir, keep_path=False)
        copy(self, "COPYING", src=self.source_folder, dst=license_dir, keep_path=False)
        copy(self, "LICENSE", src=self.source_folder, dst=license_dir, keep_path=False)
        copy(self, "*.txt", src=os.path.join(self.source_folder, "doc"), dst=os.path.join(share_dir, "doc"), keep_path=False)
        copy(self, "*", src=os.path.join(self.source_folder, "samples"), dst=os.path.join(share_dir, "samples"), keep_path=True)

        script = os.path.join(bin_dir, "safekeep")
        with open(script, "rb") as handle:
            script_data = handle.read()
        if script_data.startswith(b"#!"):
            _, rest = script_data.split(b"\n", 1)
            with open(script, "wb") as handle:
                handle.write(b"#!/usr/bin/env python3\n" + rest)
        os.chmod(script, os.stat(script).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
