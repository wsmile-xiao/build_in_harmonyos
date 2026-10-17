#!/usr/bin/env python3
"""Conan recipe for the architecture-independent French words-fr 2.1 data package."""

import os
from pathlib import Path
from typing import Iterable

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches, copy, export_conandata_patches, get,
)
from conan.tools.layout import basic_layout


class WordsFrConan(ConanFile):
    name = "words-fr"
    version = "2.1"
    package_type = "unknown"
    description = "French word list derived from GNU Aspell French 0.50-3"
    license = "GPL-2.0-or-later"
    homepage = "https://ftp.gnu.org/gnu/aspell/dict/fr/"
    url = "https://ftp.gnu.org/gnu/aspell/dict/fr/aspell-fr-0.50-3.tar.bz2"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        # No local sources or conandata patches are currently needed.
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)
    @staticmethod
    def _decode_cwl(path: Path) -> list[bytes]:
        """Decode Aspell legacy prezip v1 records with strict bounds."""
        data = Path(path).read_bytes()
        if not data or data[0] != 1:
            raise ValueError(f"{path} is not an Aspell prezip v1 word list")

        offset = 1
        previous = b""
        control = 1  # The first record has an implicit zero-length prefix.
        words: list[bytes] = []

        while True:
            if control == 0:
                if offset >= len(data):
                    raise ValueError(f"{path} has a truncated extended prefix")
                control = data[offset]
                offset += 1

            prefix_length = control - 1
            if prefix_length < 0 or prefix_length > len(previous):
                raise ValueError(f"{path} references beyond the previous word")

            word = bytearray(previous[:prefix_length])
            while offset < len(data) and data[offset] > 32:
                word.append(data[offset])
                offset += 1

            if not word:
                raise ValueError(f"{path} contains an empty word record")
            words.append(bytes(word))
            previous = bytes(word)

            if offset >= len(data):
                break
            control = data[offset]
            offset += 1

        return words

    @staticmethod
    def _sort_key(word: str) -> tuple[bytes, bytes]:
        """Match the repository words-fi dictionary key and UTF-8 tie-break."""
        encoded = word.encode("utf-8")
        primary = bytearray()
        for value in encoded:
            if value == 32 or 48 <= value <= 57 or 65 <= value <= 90 or 97 <= value <= 122:
                primary.append(value + 32 if 65 <= value <= 90 else value)
        return bytes(primary), encoded

    @classmethod
    def _normalize_words(cls, records: Iterable[bytes]) -> list[str]:
        words: set[str] = set()
        for record in records:
            base = record.split(b"/", 1)[0]
            if not base:
                raise ValueError("Aspell word list contains an empty base record")
            words.add(base.decode("iso-8859-1"))
        return sorted(words, key=cls._sort_key)

    @staticmethod
    def _source_cwl_inputs(source: Path) -> tuple[Path, Path]:
        """Validate source charset and return only the default fr-60 CWL inputs."""
        source = Path(source)
        charset_file = source / "fr.dat"
        if not charset_file.is_file():
            raise ValueError("GNU Aspell French source is missing fr.dat")
        try:
            charset_data = charset_file.read_text(encoding="ascii", errors="strict")
        except UnicodeDecodeError as exc:
            raise ValueError("fr.dat must be ASCII text") from exc

        declared_charsets = []
        for line in charset_data.splitlines():
            fields = line.split()
            if len(fields) >= 2 and fields[0].lower() == "charset":
                declared_charsets.append(fields[1].lower().replace("-", ""))
        if "iso88591" not in declared_charsets:
            raise ValueError("fr.dat does not declare the expected ISO-8859-1 charset")

        inputs = (source / "fr-40-only.cwl", source / "fr-60-only.cwl")
        missing = [path.name for path in inputs if not path.is_file()]
        if missing:
            raise ValueError(f"GNU Aspell French source is missing selected CWL inputs: {missing}")
        return inputs

    def build(self):
        source = Path(self.source_folder)
        inputs = self._source_cwl_inputs(source)
        records: list[bytes] = []
        for path in inputs:
            records.extend(self._decode_cwl(path))
        words = self._normalize_words(records)
        if len(words) != 629569:
            raise ValueError(f"unexpected words-fr entry count: {len(words)}")

        output = Path(self.build_folder) / "words-fr"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(("\n".join(words) + "\n").encode("utf-8"))

    def package(self):
        copy(
            self,
            "words-fr",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "share", "dict"),
        )
        for license_file in ("Copyright", "COPYING"):
            source_file = Path(self.source_folder) / license_file
            if not source_file.is_file():
                raise ValueError(f"GNU Aspell French source is missing {license_file}")
            copy(
                self,
                license_file,
                src=self.source_folder,
                dst=os.path.join(self.package_folder, "licenses"),
            )

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share"]
        word_file = os.path.join(self.package_folder, "share", "dict", "words-fr")
        self.buildenv_info.define_path("WORDS_FR_FILE", word_file)
        self.runenv_info.define_path("WORDS_FR_FILE", word_file)
