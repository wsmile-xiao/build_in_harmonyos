#!/usr/bin/env python3
"""Conan recipe for the American English word list words-en 2.1."""

import os
from pathlib import Path

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class WordsEnConan(ConanFile):
    name = "words-en"
    version = "2.1"
    description = "American English word-list data derived from GNU Aspell"
    license = "GPL-2.0-or-later"
    homepage = "https://ftp.gnu.org/gnu/aspell/dict/0index.html"
    url = "https://ftp.gnu.org/gnu/aspell/dict/en/"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            filename="aspell6-en-2017.08.24-0.tar.bz2",
            strip_root=True,
        )

    @staticmethod
    def _decode_cwl(path):
        """Decode the prezip v2 prefix-delta stream used by Aspell .cwl files."""
        data = Path(path).read_bytes()
        if not data or data[0] != 2:
            raise ValueError(f"{path} is not a prezip v2 word list")

        offset = 1
        previous = b""
        words = []
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
                    raise ValueError(f"{path} has a truncated prefix")
                prefix_length += data[offset]
                offset += 1
            else:
                raise ValueError(f"{path} has an invalid prefix control byte")

            if prefix_length > len(previous):
                raise ValueError(f"{path} references beyond the previous word")

            encoded = bytearray(previous[:prefix_length])
            terminal = False
            while offset < len(data):
                if (
                    data[offset] == 31
                    and offset + 1 < len(data)
                    and data[offset + 1] == 255
                ):
                    terminal = True
                    offset += 2
                    break
                if data[offset] <= 30:
                    break
                encoded.append(data[offset])
                offset += 1

            if terminal:
                if prefix_length != 0 or encoded:
                    raise ValueError(f"{path} has a non-empty prezip terminator record")
                if offset != len(data):
                    raise ValueError(f"{path} has data after the prezip terminator")
                break

            decoded = bytearray()
            index = 0
            while index < len(encoded):
                if encoded[index] == 31:
                    if (
                        index + 1 >= len(encoded)
                        or not 32 <= encoded[index + 1] < 64
                    ):
                        raise ValueError(f"{path} has an invalid escape sequence")
                    decoded.append(encoded[index + 1] - 32)
                    index += 2
                else:
                    decoded.append(encoded[index])
                    index += 1
            words.append(bytes(decoded))
            previous = bytes(encoded)

        return words

    @staticmethod
    def _dictionary_sort_key(word):
        """Match GNU sort -df under LC_ALL=C, including its whole-line tie-break."""
        primary = bytearray()
        for character in word:
            if character == 32 or 48 <= character <= 57:
                primary.append(character)
            elif 65 <= character <= 90:
                primary.append(character + 32)
            elif 97 <= character <= 122:
                primary.append(character)
        return bytes(primary), word

    def build(self):
        apply_conandata_patches(self)
        source = Path(self.source_folder)
        inputs = [source / "en-common.cwl", *sorted(source.glob("en_US*.cwl"))]
        expected = {
            "en-common.cwl",
            "en_US-w_accents-only.cwl",
            "en_US-wo_accents-only.cwl",
        }
        actual = {path.name for path in inputs if path.is_file()}
        if actual != expected:
            raise ValueError(
                f"expected American English inputs {sorted(expected)}, "
                f"found {sorted(actual)}"
            )

        words = set()
        for path in inputs:
            for entry in self._decode_cwl(path):
                word = entry.split(b"/", 1)[0]
                if word:
                    words.add(word.decode("iso-8859-1").encode("utf-8"))

        if len(words) != 123115:
            raise ValueError(f"unexpected words-en entry count: {len(words)}")

        output = Path(self.build_folder) / "words-en"
        output.parent.mkdir(parents=True, exist_ok=True)
        ordered = sorted(words, key=self._dictionary_sort_key)
        output.write_bytes(b"\n".join(ordered) + b"\n")

    def package(self):
        copy(
            self,
            "words-en",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "share", "dict"),
        )
        copy(
            self,
            "Copyright",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share"]
        word_file = os.path.join(
            self.package_folder, "share", "dict", "words-en"
        )
        self.buildenv_info.define_path("WORDS_EN_FILE", word_file)
        self.runenv_info.define_path("WORDS_EN_FILE", word_file)
