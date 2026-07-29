#!/usr/bin/env python3
"""Conan recipe for latexdiff 1.4.0."""
import os
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, save
from conan.tools.layout import basic_layout


class LatexdiffConan(ConanFile):
    name = "latexdiff"
    version = "1.4.0"
    description = "Perl tools for marking differences between LaTeX files"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/ftilmann/latexdiff"
    url = ""
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

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
        libexec = os.path.join(self.package_folder, "libexec", "latexdiff")
        bindir = os.path.join(self.package_folder, "bin")
        man1 = os.path.join(self.package_folder, "share", "man", "man1")
        os.makedirs(libexec, exist_ok=True)
        os.makedirs(bindir, exist_ok=True)
        os.makedirs(man1, exist_ok=True)

        for script in ("latexdiff-so", "latexdiff-fast", "latexdiff-vc", "latexrevise"):
            copy(self, script, src=self.source_folder, dst=libexec, keep_path=False)
            os.chmod(os.path.join(libexec, script), 0o755)

        for manpage in ("latexdiff.1", "latexdiff-vc.1", "latexrevise.1"):
            copy(self, manpage, src=self.source_folder, dst=man1, keep_path=False)

        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

        wrappers = {
            "latexdiff": "latexdiff-so",
            "latexdiff-fast": "latexdiff-fast",
            "latexdiff-vc": "latexdiff-vc",
            "latexrevise": "latexrevise",
        }
        for command, target in wrappers.items():
            wrapper = os.path.join(bindir, command)
            save(self, wrapper, self._wrapper_script(target))
            os.chmod(
                wrapper,
                stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
                stat.S_IRGRP | stat.S_IXGRP |
                stat.S_IROTH | stat.S_IXOTH,
            )

    @staticmethod
    def _wrapper_script(target):
        return f"""#!/bin/sh
set -e
case "$0" in
  */*) wrapper_path=$0 ;;
  *) wrapper_path=$(command -v "$0") || exit 127 ;;
esac
script_dir=$(CDPATH= cd -- "$(dirname -- "$wrapper_path")" && pwd)
prefix=$(CDPATH= cd -- "$script_dir/.." && pwd)
perl_bin=${{LATEXDIFF_PERL:-perl}}
exec "$perl_bin" "$prefix/libexec/latexdiff/{target}" "$@"
"""

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share", "libexec"]
