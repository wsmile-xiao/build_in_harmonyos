#!/usr/bin/env python3
"""Conan recipe for xe 1.0 - execute a command for every argument.

xe combines xargs(1) and apply(1): it builds command lines from arguments read
from stdin (or files/argv) and executes them, with ``{}`` replacement, batching
(``-N``), parallelism (``-j``), a dry-run mode (``-n``) and a shell mode (``-s``).

OHOS notes
----------
* Single-file C program (``xe.c``) with no dependencies; compiled directly with
  the OHOS clang using the upstream flags.
* Upstream ships a TAP test suite (``t/*.t`` run through ``prove`` using the
  ``tap3`` helper); it is executed in ``build()``.  ``prove`` comes from the
  device Perl.  One assertion (``-A%``) assumes a GNU echo that prints ``--``;
  OHOS's echo treats ``--`` as end-of-options, so a one-line patch switches
  that case to ``printf`` (which does not reinterpret ``--``).
* CLI tool: ``package()`` installs ``bin/xe``, the man page and the zsh
  completion; a software-level ``commands.json`` is provided.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"

_CFLAGS = "-O2 -Wall -Wno-switch -Wextra -Wwrite-strings"


class XeConan(ConanFile):
    name = "xe"
    version = "1.0"
    description = "Execute a command for every argument (xargs/apply replacement)"
    license = "CC0-1.0"
    homepage = "https://github.com/leahneukirchen/xe"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "xe OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler(self, name, fallback):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        return executables.get(name) or fallback

    def build(self):
        apply_conandata_patches(self)
        binary = os.path.join(self.build_folder, "xe")
        self.run('"{}" {} -o "{}" "{}"'.format(
            self._compiler("c", "clang"), _CFLAGS, binary,
            os.path.join(self.source_folder, "xe.c")))
        # Upstream TAP suite; the .t scripts prepend "." to PATH and use tap3.
        self.run('PATH="{}:$PATH" prove -v t'.format(self.build_folder),
                 cwd=self.source_folder)

    def package(self):
        copy(self, "xe", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "xe.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"),
             keep_path=False)
        copy(self, "_xe", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "zsh", "site-functions"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "xe")
        self.cpp_info.set_property("cmake_target_name", "xe::xe")
