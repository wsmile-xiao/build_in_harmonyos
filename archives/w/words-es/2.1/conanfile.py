#!/usr/bin/env python3
"""Conan recipe for the GNU Aspell Spanish word list, packaged as words-es 2.1."""

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


class WordsEsConan(ConanFile):
    name = "words-es"
    version = "2.1"
    description = "UTF-8 Spanish word list derived from GNU Aspell dictionary data"
    license = "GPL-2.0-only"
    homepage = "https://ftp.gnu.org/gnu/aspell/dict/es/"
    url = "https://ftp.gnu.org/gnu/aspell/dict/es/"
    package_type = "unknown"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    @staticmethod
    def _decode_cwl(path):
        """Decode Aspell's prezip v2 prefix-delta stream into raw byte records."""
        data = Path(path).read_bytes()
        if not data or data[0] != 2:
            raise ValueError(f"{path} is not a prezip v2 word list")

        offset = 1
        previous = b""
        words = []
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
                if encoded:
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
                        raise ValueError(f"{path} has an invalid escape sequence")
                    decoded.append(encoded[index + 1] - 32)
                    index += 2
                else:
                    decoded.append(encoded[index])
                    index += 1
            words.append(bytes(decoded))
            previous = bytes(encoded)

        if not terminated:
            raise ValueError(f"{path} has no prezip terminator")
        return words

    @staticmethod
    def _normalize_words(words):
        """Remove Aspell affix flags and convert its Latin-1 words to UTF-8."""
        normalized = set()
        for record in words:
            word = record.split(b"/", 1)[0]
            if not word:
                raise ValueError("the source word list contains an empty word")
            normalized.add(word.decode("latin-1").encode("utf-8"))
        return sorted(normalized)

    def build(self):
        source = Path(self.source_folder) / "es.cwl"
        words = self._normalize_words(self._decode_cwl(source))
        if len(words) != 56329:
            raise ValueError(f"unexpected words-es entry count: {len(words)}")

        output = Path(self.build_folder) / "words-es"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"\n".join(words) + b"\n")

    def package(self):
        copy(
            self,
            "words-es",
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
        self.cpp_info.libs = []
        self.cpp_info.resdirs = ["share"]
        word_list = os.path.join(self.package_folder, "share", "dict", "words-es")
        self.buildenv_info.define_path("WORDS_ES_FILE", word_list)
        self.runenv_info.define_path("WORDS_ES_FILE", word_list)
