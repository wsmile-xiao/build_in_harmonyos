#!/usr/bin/env python3
"""Conan recipe for GNU Aspell German word lists, words-de 2.1."""

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


class WordsDeConan(ConanFile):
    name = "words-de"
    version = "2.1"
    description = "German spelling dictionaries from GNU Aspell"
    license = "GPL-2.0-only"
    homepage = "http://wordlist.aspell.net/"
    url = "https://ftp.gnu.org/gnu/aspell/dict/"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        apply_conandata_patches(self)
        get(
            self,
            **self.conan_data["sources"]["standard"],
            filename="aspell-de-0.50-2.tar.bz2",
            destination=os.path.join(self.source_folder, "standard"),
            strip_root=True,
        )
        get(
            self,
            **self.conan_data["sources"]["old_spelling"],
            filename="aspell6-de-alt-2.1-1.tar.bz2",
            destination=os.path.join(self.source_folder, "old_spelling"),
            strip_root=True,
        )

    @staticmethod
    def _decode_prezip_v1(path):
        """Decode Aspell's legacy word-list-compress format (prezip v1)."""
        data = Path(path).read_bytes()
        if not data or data[0] != 1:
            raise ValueError(f"{path} is not a prezip v1 word list")

        offset = 1
        previous = bytearray()
        previous_length = 0
        control = 1
        words = []
        while control != -1:
            if control == 0:
                if offset >= len(data):
                    raise ValueError(f"{path} has a truncated extended prefix")
                control = data[offset]
                offset += 1

            prefix_length = control - 1
            if prefix_length < 0 or prefix_length > previous_length:
                raise ValueError(f"{path} has an invalid prefix length")

            word = previous[:prefix_length]
            while offset < len(data) and data[offset] > 32:
                word.append(data[offset])
                offset += 1

            if offset < len(data):
                control = data[offset]
                offset += 1
            else:
                control = -1

            previous = word
            previous_length = len(word)
            words.append(bytes(word))

        return words

    @staticmethod
    def _decode_prezip_v2(path):
        """Decode Aspell's prefix-delta word-list format (prezip v2)."""
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

    @classmethod
    def _decode_cwl(cls, path):
        data = Path(path).read_bytes()
        if not data:
            raise ValueError(f"{path} is empty")
        if data[0] == 1:
            return cls._decode_prezip_v1(path)
        if data[0] == 2:
            return cls._decode_prezip_v2(path)
        raise ValueError(f"{path} has an unsupported Aspell word-list format")

    @staticmethod
    def _plain_utf8_words(words):
        """Strip Aspell affix suffixes and convert source Latin-1 words to UTF-8."""
        return {
            word.split(b"/", 1)[0].decode("latin-1").encode("utf-8")
            for word in words
            if word.split(b"/", 1)[0]
        }

    def build(self):
        standard = Path(self.source_folder) / "standard"
        old_spelling = Path(self.source_folder) / "old_spelling"
        new_inputs = [
            standard / "de-only.cwl",
            standard / "de_DE-only.cwl",
            standard / "de_CH-only.cwl",
        ]
        old_input = old_spelling / "de-alt.cwl"
        if not all(path.is_file() for path in [*new_inputs, old_input]):
            raise ValueError("the two Aspell source archives are missing expected .cwl files")

        modern_words = set()
        for path in new_inputs:
            modern_words.update(self._plain_utf8_words(self._decode_cwl(path)))
        old_words = self._plain_utf8_words(self._decode_cwl(old_input))

        if len(modern_words) != 304736:
            raise ValueError(f"unexpected ngerman entry count: {len(modern_words)}")
        if len(old_words) != 76258:
            raise ValueError(f"unexpected ogerman entry count: {len(old_words)}")

        output = Path(self.build_folder) / "dict"
        output.mkdir(parents=True, exist_ok=True)
        (output / "ngerman").write_bytes(b"\n".join(sorted(modern_words)) + b"\n")
        (output / "german").write_bytes((output / "ngerman").read_bytes())
        (output / "ogerman").write_bytes(b"\n".join(sorted(old_words)) + b"\n")

    def package(self):
        copy(
            self,
            "german",
            src=os.path.join(self.build_folder, "dict"),
            dst=os.path.join(self.package_folder, "share", "dict"),
        )
        copy(
            self,
            "ngerman",
            src=os.path.join(self.build_folder, "dict"),
            dst=os.path.join(self.package_folder, "share", "dict"),
        )
        copy(
            self,
            "ogerman",
            src=os.path.join(self.build_folder, "dict"),
            dst=os.path.join(self.package_folder, "share", "dict"),
        )
        copy(
            self,
            "COPYING",
            src=os.path.join(self.source_folder, "standard"),
            dst=os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "Copyright",
            src=os.path.join(self.source_folder, "standard"),
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share"]
        self.buildenv_info.define_path(
            "WORDS_DE_FILE", os.path.join(self.package_folder, "share", "dict", "ngerman")
        )
        self.runenv_info.define_path(
            "WORDS_DE_FILE", os.path.join(self.package_folder, "share", "dict", "ngerman")
        )
        self.buildenv_info.define_path(
            "WORDS_DE_OLD_FILE", os.path.join(self.package_folder, "share", "dict", "ogerman")
        )
        self.runenv_info.define_path(
            "WORDS_DE_OLD_FILE", os.path.join(self.package_folder, "share", "dict", "ogerman")
        )
