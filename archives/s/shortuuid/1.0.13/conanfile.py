#!/usr/bin/env python3
"""Conan recipe candidate for the pure Python shortuuid 1.0.13 library."""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, get, save
from conan.tools.layout import basic_layout


class ShortuuidConan(ConanFile):
    name = "shortuuid"
    version = "1.0.13"
    description = "Concise, unambiguous, URL-safe UUIDs"
    license = "BSD-3-Clause"
    homepage = "https://github.com/skorokithakis/shortuuid"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "unknown"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True,
            extract_filter="data")

    def package(self):
        source = os.path.join(self.source_folder, "shortuuid")
        target = os.path.join(self.package_folder, "lib", "python", "shortuuid")
        for name in ("__init__.py", "main.py", "cli.py", "django_fields.py",
                     "py.typed"):
            if not copy(self, name, src=source, dst=target, keep_path=False):
                raise ConanException(f"shortuuid source file is missing: {name}")
        if not copy(self, "COPYING", src=self.source_folder,
                    dst=os.path.join(self.package_folder, "licenses"),
                    keep_path=False):
            raise ConanException("shortuuid COPYING was not packaged")
        command = os.path.join(self.package_folder, "bin", "shortuuid")
        save(self, command,
             '#!/bin/sh\n'
             'command_dir=$(CDPATH= cd "$(dirname "$0")" && pwd)\n'
             'PYTHONPATH="$command_dir/../lib/python${PYTHONPATH:+:$PYTHONPATH}" '
             'exec python3 -m shortuuid.cli "$@"\n')
        os.chmod(command, 0o755)

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PYTHONPATH", os.path.join(self.package_folder, "lib", "python"))
