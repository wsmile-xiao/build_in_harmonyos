#!/usr/bin/env python3
"""Conan recipe for the Italian words list packaged as words-it 2.1."""

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


class WordsItConan(ConanFile):
    name = "words-it"
    version = "2.1"
    description = "Italian word-list data derived from GNU Aspell"
    license = "GPL-2.0-or-later"
    homepage = "https://ftp.gnu.org/gnu/aspell/dict/it/"
    url = "https://ftp.gnu.org/gnu/aspell/dict/it/aspell6-it-2.2_20050523-0.tar.bz2"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            filename="aspell6-it-2.2_20050523-0.tar.bz2",
            strip_root=True,
        )

    @staticmethod
    def _decode_cwl(path):
        """Decode Aspell's prezip prefix-delta format into source bytes."""
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
                    if index + 1 >= len(encoded) or not 32 <= encoded[index + 1] < 64:
                        raise ValueError(f"{path} has an invalid escape sequence")
                    decoded.append(encoded[index + 1] - 32)
                    index += 2
                else:
                    decoded.append(encoded[index])
                    index += 1
            words.append(bytes(decoded))
            previous = bytes(encoded)

        return words

    def build(self):
        apply_conandata_patches(self)
        source = Path(self.source_folder) / "it.cwl"
        words = set()
        for raw_word in self._decode_cwl(source):
            try:
                words.add(raw_word.decode("iso8859-15"))
            except UnicodeDecodeError as error:
                raise ValueError(f"{source} contains invalid ISO-8859-15 data") from error

        if len(words) != 92034:
            raise ValueError(f"unexpected words-it entry count: {len(words)}")

        output = Path(self.build_folder) / "words-it"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(("\n".join(sorted(words)) + "\n").encode("utf-8"))

    def package(self):
        copy(
            self,
            "words-it",
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
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share"]
        installed_word_list = os.path.join(
            self.package_folder, "share", "dict", "words-it"
        )
        self.buildenv_info.define_path("WORDS_IT_FILE", installed_word_list)
        self.runenv_info.define_path("WORDS_IT_FILE", installed_word_list)
