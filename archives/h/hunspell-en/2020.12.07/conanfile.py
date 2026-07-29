#!/usr/bin/env python3
"""Conan recipe for the English Hunspell dictionaries released 2020.12.07."""

import os
import shutil
from pathlib import Path

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import copy, download, get, replace_in_file, unzip
from conan.tools.layout import basic_layout


class HunspellEnConan(ConanFile):
    name = "hunspell-en"
    version = "2020.12.07"
    description = "English Hunspell dictionaries derived from SCOWL"
    license = "BSD-3-Clause AND MIT AND LGPL-2.1-or-later"
    homepage = "http://wordlist.aspell.net/"
    url = "https://github.com/en-wl/wordlist"

    settings = "os", "compiler", "build_type", "arch"

    _release_keys = (
        "en_US",
        "en_CA",
        "en_AU",
        "en_GB_ise",
        "en_GB_ize",
    )

    def layout(self):
        basic_layout(self)

    def source(self):
        release_dir = os.path.join(self.source_folder, "release")
        for key in self._release_keys:
            get(
                self,
                **self.conan_data["sources"][key],
                filename=f"{key}.zip",
                destination=release_dir,
            )

        test_source = self.conan_data["sources"]["upstream_tests"]
        download(
            self,
            test_source["url"],
            os.path.join(
                self.source_folder, "wordlist-rel-2020.12.07.tar.gz"
            ),
            sha256=test_source["sha256"],
        )

    @staticmethod
    def _validate_dictionary(dictionary):
        lines = Path(dictionary).read_text(
            encoding="utf-8", errors="strict"
        ).splitlines()
        if not lines or not lines[0].isdigit():
            raise ValueError(f"{dictionary} has no numeric entry count")
        if int(lines[0]) != len(lines) - 1:
            raise ValueError(
                f"{dictionary} declares {lines[0]} entries but contains "
                f"{len(lines) - 1}"
            )

    def build(self):
        release_dir = Path(self.source_folder) / "release"
        expected = ("en_US", "en_CA", "en_AU", "en_GB-ise", "en_GB-ize")
        for locale in expected:
            aff = release_dir / f"{locale}.aff"
            dic = release_dir / f"{locale}.dic"
            if not aff.is_file() or not dic.is_file():
                raise ValueError(f"missing release dictionary pair for {locale}")
            if "SET UTF-8" not in aff.read_text(encoding="utf-8"):
                raise ValueError(f"{aff} does not declare UTF-8")
            self._validate_dictionary(dic)

        if can_run(self) and str(self.settings.os) == "Linux":
            upstream_dir = os.path.join(self.build_folder, "upstream-tests")
            unzip(
                self,
                os.path.join(
                    self.source_folder, "wordlist-rel-2020.12.07.tar.gz"
                ),
                destination=upstream_dir,
                strip_root=True,
            )
            # SQLite 3.37+ treats the upstream unquoted "\t" as a
            # two-character separator. Quoting the existing escape preserves
            # the intended tab separator on both old and current SQLite.
            replace_in_file(
                self,
                os.path.join(
                    upstream_dir, "scowl", "sql", "create.sql"
                ),
                ".separator \\t",
                '.separator "\\t"',
            )
            self.run("make prep", cwd=upstream_dir)
            self.run("make test", cwd=upstream_dir)
        else:
            self.output.info(
                "Non-Linux build: the canonical wordlist make-test suite "
                "runs in the native Linux validation stage."
            )

    def package(self):
        release_dir = os.path.join(self.source_folder, "release")
        dictionary_dir = os.path.join(
            self.package_folder, "share", "hunspell"
        )
        os.makedirs(dictionary_dir, exist_ok=True)
        copy(self, "*.aff", src=release_dir, dst=dictionary_dir)
        copy(self, "*.dic", src=release_dir, dst=dictionary_dir)

        for extension in ("aff", "dic"):
            shutil.copy2(
                os.path.join(release_dir, f"en_GB-ise.{extension}"),
                os.path.join(dictionary_dir, f"en_GB.{extension}"),
            )

        copy(
            self,
            "README_*.txt",
            src=release_dir,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share"]
        dictionary_dir = os.path.join(
            self.package_folder, "share", "hunspell"
        )
        self.buildenv_info.define_path("DICPATH", dictionary_dir)
        self.runenv_info.define_path("DICPATH", dictionary_dir)
