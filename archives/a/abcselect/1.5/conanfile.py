#!/usr/bin/env python3
"""Conan recipe for abcselect 1.5 — extract parts from abc music files.

abcselect is a Perl script tool for extracting parts, movements, etc from
files in the abc format of music notation. No compilation needed.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AbcselectConan(ConanFile):
    name = "abcselect"
    version = "1.5"
    description = "Extract parts, movements, etc from abc music files"
    license = "GPL-2.0-or-later"
    homepage = "https://www.lautengesellschaft.de/cdmm/"
    url = "https://www.lautengesellschaft.de/cdmm/"
    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("perl/5.42.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        # tar 包仅含单个顶层目录 abcselect/，剥离根目录使脚本直接位于
        # source_folder 根（package() 按此路径查找 abcselect / abcselect.1）。
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

        # Install script
        script = os.path.join(src, "abcselect")
        if os.path.isfile(script):
            dest = os.path.join(bindir, "abcselect")
            shutil.copy2(script, dest)
            # Fix shebang: OHOS has no /usr/bin/perl; use env for PATH lookup
            with open(dest, "r") as fh:
                content = fh.read()
            if content.startswith("#!/"):
                first_newline = content.index("\n")
                content = "#!/usr/bin/env perl" + content[first_newline:]
            with open(dest, "w") as fh:
                fh.write(content)
            os.chmod(dest, 0o755)
        else:
            raise ConanException(f"abcselect script not found in source: {script}")

        # Install man page (uncompressed, as source is not gzipped)
        manpage = os.path.join(src, "abcselect.1")
        if os.path.isfile(manpage):
            shutil.copy2(manpage, os.path.join(mandir, "abcselect.1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []