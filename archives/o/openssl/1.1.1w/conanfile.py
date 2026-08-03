#!/usr/bin/env python3
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class OpensslConan(ConanFile):
    name = "openssl"
    version = "1.1.1w"
    description = "TLS/SSL and cryptographic library"
    license = "OpenSSL"
    homepage = "https://www.openssl.org/"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("openssl is only supported on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("openssl/1.1.1w supports OHOS armv8 only")

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            filename=f"openssl-{self.version}.tar.gz",
            strip_root=True,
        )
        apply_conandata_patches(self)

    def _target(self):
        if self.settings.os == "OHOS":
            return "openharmony-aarch64"
        if self.settings.arch == "armv8":
            return "linux-aarch64"
        if self.settings.arch == "x86_64":
            return "linux-x86_64"
        return "linux-generic32"

    def build(self):
        prefix = self.package_folder
        openssldir = os.path.join(prefix, "ssl")
        cc = os.environ.get("CC", "clang")

        args = [
            "perl",
            "./Configure",
            f"--prefix={prefix}",
            f"--openssldir={openssldir}",
            "no-asm",
            f"CC={cc}",
            self._target(),
        ]
        if not self.options.shared:
            args.append("no-shared")
        if self.options.get_safe("fPIC"):
            args.append("-fPIC")

        self.run(" ".join(args), cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

        self.run("make test", cwd=self.source_folder)

    def package(self):
        self.run("make install_sw", cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = ["ssl", "crypto"]
        self.cpp_info.system_libs = ["dl", "pthread"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
