#!/usr/bin/env python3
"""Conan recipe - utftex 1.31."""
import os
import shlex

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class UtftexConan(ConanFile):
    name = "utftex"
    version = "1.31"
    description = "Render TeX math expressions as UTF-8 terminal text"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/bartp5/libtexprintf"
    url = "https://github.com/bartp5/libtexprintf"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        src_dir = os.path.join(self.source_folder, "src")
        self._write_config_header(src_dir)
        self.run("sh gen_errorflags.sh boxes.c drawbox.c lexer.c parser.c", cwd=src_dir, env="conanbuild")
        self.run("sh gentexprintfsymbols.sh", cwd=src_dir, env="conanbuild")
        self._build_binary(
            "utftex",
            [
                "main.c", "testfonts.c", "texprintf.c", "boxes.c", "error.c",
                "stringutils.c", "drawbox.c", "lexer.c", "parser.c",
            ],
            src_dir,
        )
        self._build_binary(
            "utfstringinfo",
            ["utf2unicode.c", "stringutils.c", "error.c"],
            src_dir,
        )

    def _compiler_path(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}) or {}
        return compilers.get("c") or "cc"

    def _write_config_header(self, src_dir):
        config = os.path.join(src_dir, "config.h")
        content = "\n".join([
            "#pragma once",
            "#define HAVE_GETOPT_H 1",
            '#define UTFTEXVERSION "1.31"',
            '#define PACKAGE_STRING "libtexprintf 1.31"',
            "",
        ])
        with open(config, "w", encoding="utf-8") as handle:
            handle.write(content)

    def _build_binary(self, binary, sources, src_dir):
        cc = shlex.quote(self._compiler_path())
        source_args = " ".join(shlex.quote(source) for source in sources)
        ldflags = ["-lm"]
        if str(self.settings.os) == "OHOS":
            ldflags.append("-fuse-ld=/data/service/hnp/bin/ld")
        command = f"{cc} -I. -Wall -O2 -fPIC -o {shlex.quote(binary)} {source_args} {' '.join(ldflags)}"
        self.run(command, cwd=src_dir, env="conanbuild")

    def package(self):
        src_dir = os.path.join(self.source_folder, "src")
        bin_dir = os.path.join(self.package_folder, "bin")
        man1_dir = os.path.join(self.package_folder, "share", "man", "man1")
        man3_dir = os.path.join(self.package_folder, "share", "man", "man3")
        doc_dir = os.path.join(self.package_folder, "share", "doc", "utftex")

        copy(self, "utftex", src=src_dir, dst=bin_dir)
        copy(self, "utfstringinfo", src=src_dir, dst=bin_dir)
        copy(self, "*.1", src=src_dir, dst=man1_dir)
        copy(self, "*.3", src=src_dir, dst=man3_dir)
        copy(self, "COPYING", src=self.source_folder, dst=doc_dir)
        copy(self, "README*", src=self.source_folder, dst=doc_dir)
        for binary in ("utftex", "utfstringinfo"):
            path = os.path.join(bin_dir, binary)
            if os.path.exists(path):
                os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
