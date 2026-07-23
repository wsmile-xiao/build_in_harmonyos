#!/usr/bin/env python3
"""Conan recipe - utftex 1.31."""
import os
import shlex
import shutil

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

    def _optimization_flags(self):
        build_type = str(self.settings.build_type)
        if build_type == "Debug":
            return ["-O0", "-g"]
        if build_type == "RelWithDebInfo":
            return ["-O2", "-g"]
        if build_type == "MinSizeRel":
            return ["-Os"]
        return ["-O2"]

    def _linker_flag(self):
        if str(self.settings.os) != "OHOS":
            return []
        linker = os.environ.get("LD")
        if not linker:
            linker = shutil.which("ld.lld") or shutil.which("ld")
        linker_name = os.path.basename(linker) if linker else ""
        linker_map = {
            "ld.lld": "lld",
            "lld": "lld",
            "ld.gold": "gold",
            "gold": "gold",
            "ld.bfd": "bfd",
            "bfd": "bfd",
        }
        linker_name = linker_map.get(linker_name)
        return [f"-fuse-ld={linker_name}"] if linker_name else []

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
        cflags = ["-I.", "-Wall", *self._optimization_flags(), "-fPIC"]
        ldflags = ["-lm", *self._linker_flag()]
        command = (
            f"{cc} {' '.join(shlex.quote(flag) for flag in cflags)} "
            f"-o {shlex.quote(binary)} {source_args} "
            f"{' '.join(shlex.quote(flag) for flag in ldflags)}"
        )
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
                self._sign_binary(path)

    def _sign_binary(self, path):
        os.chmod(path, 0o755)
        sign_tool = shutil.which("binary-sign-tool")
        objcopy = shutil.which("llvm-objcopy")
        if str(self.settings.os) != "OHOS" or not (sign_tool and objcopy):
            return
        tmp_signed = path + ".signed"
        self.run(f"{shlex.quote(objcopy)} --remove-section .codesign {shlex.quote(path)} 2>/dev/null || true", quiet=True)
        self.run(
            f"{shlex.quote(sign_tool)} sign -inFile {shlex.quote(path)} "
            f"-outFile {shlex.quote(tmp_signed)} -selfSign 1",
            quiet=True,
        )
        os.replace(tmp_signed, path)
        os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
