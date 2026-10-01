#!/usr/bin/env python3
"""Conan recipe for the Finnish words-fi 2.1 data package."""

import os
from pathlib import Path
from typing import Iterable

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class WordsFiConan(ConanFile):
    name = "words-fi"
    version = "2.1"
    package_type = "unknown"
    description = "Finnish word list derived from GNU Aspell Finnish 0.7-0"
    license = "GPL-2.0-or-later"
    homepage = "https://ftp.gnu.org/gnu/aspell/dict/fi/"
    url = "https://ftp.gnu.org/gnu/aspell/dict/fi/aspell6-fi-0.7-0.tar.bz2"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    @staticmethod
    def _decode_cwl(path: Path) -> list[bytes]:
        """Decode Aspell prezip v2 prefix-delta records with strict bounds."""
        data = Path(path).read_bytes()
        if not data or data[0] != 2:
            raise ValueError(f"{path} is not a prezip v2 word list")

        offset = 1
        previous = b""
        words: list[bytes] = []
        terminated = False

        while offset < len(data):
            control = data[offset]
            offset += 1
            if control < 30:
                prefix_length = control
            elif control == 30:
                prefix_length = 30
                while offset < len(data) and data[offset] == 255:
                    prefix_length += 255
                    offset += 1
                if offset >= len(data):
                    raise ValueError(f"{path} has a truncated prefix length")
                prefix_length += data[offset]
                offset += 1
            else:
                raise ValueError(f"{path} has an invalid prefix control byte")

            if prefix_length > len(previous):
                raise ValueError(f"{path} references beyond the previous word")

            encoded = bytearray(previous[:prefix_length])
            is_terminator = False
            while offset < len(data):
                if data[offset] == 31 and offset + 1 < len(data) and data[offset + 1] == 255:
                    is_terminator = True
                    offset += 2
                    break
                if data[offset] <= 30:
                    break
                encoded.append(data[offset])
                offset += 1

            if is_terminator:
                if prefix_length != 0 or encoded:
                    raise ValueError(f"{path} has a non-empty prezip terminator record")
                if offset != len(data):
                    raise ValueError(f"{path} has data after the prezip terminator")
                terminated = True
                break

            decoded = bytearray()
            index = 0
            while index < len(encoded):
                if encoded[index] == 31:
                    if index + 1 >= len(encoded) or not 32 <= encoded[index + 1] < 64:
                        raise ValueError(f"{path} has an invalid or truncated escape sequence")
                    decoded.append(encoded[index + 1] - 32)
                    index += 2
                else:
                    decoded.append(encoded[index])
                    index += 1

            words.append(bytes(decoded))
            # Prefix deltas refer to the pre-unescaped representation.
            previous = bytes(encoded)

        if not terminated:
            raise ValueError(f"{path} is missing the prezip v2 terminator")
        return words

    @staticmethod
    def _sort_key(word: str) -> tuple[bytes, bytes]:
        """Match LC_ALL=C sort -df: ASCII dictionary key then full line bytes."""
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

    def build(self):
        source = Path(self.source_folder)
        charset_file = source / "fi.dat"
        if not charset_file.is_file():
            raise ValueError("GNU Aspell Finnish source is missing fi.dat")
        charset_data = charset_file.read_text(encoding="ascii", errors="strict").lower()
        if "charset iso-8859-1" not in charset_data:
            raise ValueError("fi.dat does not declare the expected ISO-8859-1 charset")

        inputs = sorted(source.glob("fi.cwl"))
        if len(inputs) != 1:
            raise ValueError(f"expected exactly one Finnish fi.cwl input, found {len(inputs)}")
        words = self._normalize_words(self._decode_cwl(inputs[0]))
        if len(words) != 88328:
            raise ValueError(f"unexpected words-fi entry count: {len(words)}")

        output = Path(self.build_folder) / "words-fi"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(("\n".join(words) + "\n").encode("utf-8"))

    def package(self):
        copy(
            self,
            "words-fi",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "share", "dict"),
        )
        for license_file in ("Copyright", "COPYING"):
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
        word_file = os.path.join(self.package_folder, "share", "dict", "words-fi")
        self.buildenv_info.define_path("WORDS_FI_FILE", word_file)
        self.runenv_info.define_path("WORDS_FI_FILE", word_file)
