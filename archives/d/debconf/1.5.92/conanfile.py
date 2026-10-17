from conan import ConanFile
from conan.tools.files import copy, download
from conan.tools.layout import basic_layout
import os


class DebconfConan(ConanFile):
    name = "debconf"
    version = "1.5.92"
    description = "Debian package configuration management system (pure Perl)"
    license = "BSD-2-Clause"
    homepage = "https://salsa.debian.org/pkg-debconf/debconf"
    url = ""
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        tarball = "debconf_1.5.92.tar.xz"
        source = self.conan_data["sources"]
        download(self, source["url"], filename=tarball,
                 sha256=source["sha256"])
        self.run(
            f"tar -xJf {tarball} --strip-components=1 --no-same-owner "
            "--transform='s|^work/debconf$|work/debconf.tool|'",
            cwd=self.source_folder)
        os.remove(os.path.join(self.source_folder, tarball))

    def build(self):
        # The upstream Makefile only builds docs/translations; runtime is Perl.
        pass

    def package(self):
        src = self.source_folder
        lib_dest = os.path.join(self.package_folder, "lib", "perl5")
        for root, _dirs, files in os.walk(os.path.join(src, "Debconf")):
            for filename in files:
                if filename.endswith(".pm"):
                    rel = os.path.relpath(os.path.join(root, filename), src)
                    copy(self, rel, src, lib_dest)

        bin_dest = os.path.join(self.package_folder, "bin")
        for filename in os.listdir(src):
            if (filename.startswith("debconf") or filename in
                    ("confmodule", "confmodule.sh", "check_db.pl")):
                path = os.path.join(src, filename)
                if os.path.isfile(path) and os.access(path, os.X_OK):
                    copy(self, filename, src, bin_dest)
        # HMDFS is case-insensitive: work/Debconf/ conflicts with work/debconf.
        transformed = os.path.join(bin_dest, "debconf.tool")
        if os.path.isfile(transformed):
            os.rename(transformed, os.path.join(bin_dest, "debconf"))

        for filename, destination in (("debconf.conf", "etc/debconf"),
                                      ("debconf.py", "lib")):
            path = os.path.join(src, filename)
            if os.path.isfile(path):
                copy(self, filename, src,
                     os.path.join(self.package_folder, destination))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
