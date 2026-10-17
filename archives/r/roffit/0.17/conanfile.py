#!/usr/bin/env python3
"""Conan recipe for roffit 0.17 — convert nroff man pages to HTML.

roffit is a single Perl script tool by Daniel Stenberg. No compilation
needed. The OHOS adaptation replaces the non-core CPAN dependency
HTML::Entities with an equivalent pure-Perl implementation (see
patches/0001-roffit.patch) so the script runs with the perl package
published in the ohpcd registry.
"""
import os
import shutil
import stat

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class RoffitConan(ConanFile):
    name = "roffit"
    version = "0.17"
    description = "Convert nroff man pages to HTML"
    license = "curl"  # SPDX: curl (MIT-style, Daniel Stenberg)
    homepage = "https://github.com/bagder/roffit"
    url = "https://github.com/bagder/roffit"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("perl/5.42.2.3")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        self.output.info("No compilation needed: Perl script tool")

    def package(self):
        src = self.source_folder
        pkg = self.package_folder

        bindir = os.path.join(pkg, "bin")
        mandir = os.path.join(pkg, "share", "man", "man1")
        os.makedirs(bindir, exist_ok=True)
        os.makedirs(mandir, exist_ok=True)

        script = os.path.join(src, "roffit")
        if os.path.isfile(script):
            dest = os.path.join(bindir, "roffit")
            shutil.copy2(script, dest)
            # OHOS has no /usr/bin/perl; use env for PATH lookup
            with open(dest, "r") as fh:
                content = fh.read()
            if content.startswith("#!/"):
                first_newline = content.index("\n")
                content = "#!/usr/bin/env perl" + content[first_newline:]
            with open(dest, "w") as fh:
                fh.write(content)
            os.chmod(dest, os.stat(dest).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        else:
            raise ConanException(f"roffit script not found in source: {script}")

        manpage = os.path.join(src, "roffit.1")
        if os.path.isfile(manpage):
            shutil.copy2(manpage, os.path.join(mandir, "roffit.1"))

        license_file = os.path.join(src, "LICENSE")
        if os.path.isfile(license_file):
            licdir = os.path.join(pkg, "licenses")
            os.makedirs(licdir, exist_ok=True)
            shutil.copy2(license_file, os.path.join(licdir, "LICENSE"))

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
