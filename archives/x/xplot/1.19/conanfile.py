#!/usr/bin/env python3
"""Conan recipe for xplot 1.19 (Makefile)."""

import os
import shlex
import shutil
import stat
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class XplotConan(ConanFile):
    name = "xplot"
    version = "1.19"
    description = "X datafile plotter for tabulated functions"
    license = "GPL-2.0-or-later"
    homepage = "https://sources.debian.org/src/xplot/1.19-9.2/"
    url = "https://archive.ubuntu.com/ubuntu/pool/universe/x/xplot/"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"xplot supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        self.requires("libforms/1.2.4")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)

        source = Path(self.source_folder)
        libforms = self.dependencies["libforms"]
        forms_header = Path(libforms.package_folder, "include", "forms.h")
        if not forms_header.is_file():
            raise ConanException(f"libforms public header is missing: {forms_header}")

        # This source uses the historic <X11/forms.h> include spelling while
        # libforms/1.2.4 installs the header as <forms.h>. Keep the compatibility
        # header in Conan's private build folder rather than editing upstream.
        compatibility_include = Path(self.build_folder, "compat-include")
        x11_include = compatibility_include / "X11"
        x11_include.mkdir(parents=True, exist_ok=True)
        shutil.copy2(forms_header, x11_include / "forms.h")

        include_dirs = [str(compatibility_include)]
        include_dirs.extend(self._dependency_dirs("includedirs"))
        include_dirs.append(str(source / "libfli" / "lib"))
        include_dirs = list(dict.fromkeys(include_dirs))

        library_dirs = self._dependency_dirs("libdirs")
        if not library_dirs:
            raise ConanException("libforms dependency has no materialized library directory")

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "clang")

        cflags = [
            "-O2",
            "-g",
            "-Wall",
            r'-DVER=\"1.19\"',
            r'-DHELPFILE=\"/usr/local/share/xplot/xplot.help\"',
        ]
        cflags.extend(f"-I{directory}" for directory in include_dirs)
        fli_cflags = " ".join(f"-I{directory}" for directory in include_dirs)

        temporary = Path(self.build_folder, ".tmp")
        temporary.mkdir(parents=True, exist_ok=True)
        build_env = Environment()
        build_env.define_path("TMPDIR", str(temporary))

        command = " ".join(
            (
                "make -C src -j1",
                f"CC={shlex.quote(cc)}",
                f"CFLAGS={shlex.quote(' '.join(cflags))}",
                f"FORM_LIB={shlex.quote(' '.join(f'-L{path}' for path in library_dirs))}",
                f"FLI_LIB={shlex.quote('-L' + str(source / 'libfli' / 'lib'))}",
                f"XPLOT_FLI_CFLAGS={shlex.quote(fli_cflags)}",
                "xplot",
            )
        )
        with build_env.vars(self).apply():
            self.run(command, cwd=str(source), env="conanbuild")

        executable = source / "src" / "xplot"
        if not executable.is_file() or executable.stat().st_size == 0:
            raise ConanException(f"xplot executable was not built: {executable}")

    def package(self):
        source = Path(self.source_folder)
        binary = Path(self.package_folder, "bin", "xplot")
        binary.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / "src" / "xplot", binary)
        binary.chmod(binary.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        help_directory = Path(self.package_folder, "share", "xplot")
        help_directory.mkdir(parents=True, exist_ok=True)
        copy(
            self,
            "xplot.help",
            src=str(source),
            dst=str(help_directory),
            keep_path=False,
        )
        manual_directory = Path(self.package_folder, "share", "man", "man1")
        manual_directory.mkdir(parents=True, exist_ok=True)
        copy(
            self,
            "xplot.1",
            src=str(source / "src"),
            dst=str(manual_directory),
            keep_path=False,
        )

        license_directory = Path(self.package_folder, "licenses")
        license_directory.mkdir(parents=True, exist_ok=True)
        copy(self, "COPYING", src=str(source), dst=str(license_directory), keep_path=False)
        copy(self, "GPL", src=str(source), dst=str(license_directory), keep_path=False)

        if str(self.settings.os) == "OHOS":
            self._sign_ohos_elf(binary)

        missing = [
            str(path.relative_to(self.package_folder))
            for path in (
                binary,
                help_directory / "xplot.help",
                manual_directory / "xplot.1",
            )
            if not path.is_file() or path.stat().st_size == 0
        ]
        if not list(license_directory.glob("*")):
            missing.append("licenses/*")
        if missing:
            raise ConanException(f"xplot package is incomplete: {missing}")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
        self.runenv_info.define_path(
            "XPLOT_HELPFILE",
            os.path.join(self.package_folder, "share", "xplot", "xplot.help"),
        )

    def _dependency_dirs(self, field):
        directories = []
        for dependency in self.dependencies.host.values():
            for directory in getattr(dependency.cpp_info, field):
                if not os.path.isabs(directory):
                    directory = os.path.join(dependency.package_folder, directory)
                if os.path.isdir(directory) and directory not in directories:
                    directories.append(directory)
        return directories

    @staticmethod
    def _sign_ohos_elf(path):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("HarmonyOS packaging requires binary-sign-tool and llvm-readelf")

        signed = str(path) + ".signed"
        Path(signed).unlink(missing_ok=True)
        subprocess.run(
            [signer, "sign", "-inFile", str(path), "-outFile", signed, "-selfSign", "1"],
            check=True,
            timeout=60,
        )
        sections = subprocess.run(
            [readelf, "-SW", signed],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException(f"signed xplot ELF has an invalid .codesign section: {path}")

        os.chmod(signed, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        os.replace(signed, path)
