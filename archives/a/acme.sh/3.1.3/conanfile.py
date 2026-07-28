#!/usr/bin/env python3
"""Conan recipe for acme.sh 3.1.3."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class AcmeShConan(ConanFile):
    name = "acme.sh"
    version = "3.1.3"
    description = "Pure shell ACME client"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/acmesh-official/acme.sh"
    url = ""
    package_type = "application"

    settings = "os", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        pass

    def package(self):
        libexec = os.path.join(self.package_folder, "libexec", "acme.sh")
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(libexec, exist_ok=True)
        os.makedirs(bindir, exist_ok=True)

        copy(self, "acme.sh", src=self.source_folder, dst=libexec, keep_path=False)
        for dirname in ("dnsapi", "deploy", "notify"):
            copy(self, "*", src=os.path.join(self.source_folder, dirname),
                 dst=os.path.join(libexec, dirname), keep_path=True)
        copy(self, "LICENSE.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

        real_script = os.path.join(libexec, "acme.sh")
        os.chmod(real_script, 0o755)

        wrapper = os.path.join(bindir, "acme.sh")
        with open(wrapper, "w", encoding="utf-8", newline="\n") as f:
            f.write("#!/usr/bin/env sh\n")
            f.write("case \"$0\" in\n")
            f.write("  */*) wrapper_path=$0 ;;\n")
            f.write("  *) wrapper_path=$(command -v \"$0\") || exit 127 ;;\n")
            f.write("esac\n")
            f.write("script_dir=$(CDPATH= cd -- \"$(dirname -- \"$wrapper_path\")\" && pwd)\n")
            f.write("exec \"$script_dir/../libexec/acme.sh/acme.sh\" \"$@\"\n")
        os.chmod(wrapper, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["libexec"]
