#!/usr/bin/env python3
"""Conan recipe - pass-otp 1.2.0 (password-store OTP extension)."""
import os

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class PassOtpConan(ConanFile):
    name = "pass-otp"
    version = "1.2.0"
    description = "Pass extension for managing one-time-password tokens"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/tadfisher/pass-otp"
    url = "https://github.com/tadfisher/pass-otp"
    package_type = "application"

    settings = "os", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        self.output.info("Pure shell extension; no native build step required")

    def package(self):
        ext_dir = os.path.join(self.package_folder, "lib", "password-store", "extensions")
        doc_dir = os.path.join(self.package_folder, "share", "doc", "pass-otp")
        man_dir = os.path.join(self.package_folder, "share", "man", "man1")

        copy(self, "otp.bash", src=self.source_folder, dst=ext_dir)
        copy(self, "pass-otp.1", src=self.source_folder, dst=man_dir)
        copy(self, "README*", src=self.source_folder, dst=doc_dir)
        copy(self, "COPYING", src=self.source_folder, dst=doc_dir)
        copy(self, "LICENSE*", src=self.source_folder, dst=doc_dir)

        extension = os.path.join(ext_dir, "otp.bash")
        if os.path.exists(extension):
            os.chmod(extension, 0o644)

    def package_id(self):
        self.info.clear()

    def package_info(self):
        ext_dir = os.path.join(self.package_folder, "lib", "password-store", "extensions")
        self.runenv_info.define_path("PASSWORD_STORE_EXTENSIONS_DIR", ext_dir)
        self.cpp_info.libdirs = ["lib"]
