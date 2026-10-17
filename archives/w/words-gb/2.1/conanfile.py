#!/usr/bin/env python3
"""Conan recipe for the British English words list packaged as words-gb 2.1."""

import os
from pathlib import Path

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class WordsGbConan(ConanFile):
    name = "words-gb"
    version = "2.1"
    description = "British English word list derived from GNU Aspell English data"
    license = "LicenseRef-SCOWL"
    homepage = "http://wordlist.aspell.net/"
    url = "https://ftp.gnu.org/gnu/aspell/dict/en/"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            filename="aspell6-en-2017.08.24-0.tar.bz2",
            strip_root=True,
        )

    @staticmethod
    def _decode_cwl(path):
        """Decode Aspell's documented prezip prefix-delta format."""
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
                # GNU Aspell writes a distinct empty record before 0x1f 0xff.
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
        inputs = [
            os.path.join(self.source_folder, "en-common.cwl"),
            *sorted(Path(self.source_folder).glob("en_GB*.cwl")),
        ]
        if len(inputs) != 7:
            raise ValueError(f"expected 7 British word-list inputs, found {len(inputs)}")

        words = set()
        for path in inputs:
            words.update(self._decode_cwl(path))

        output = Path(self.build_folder) / "words-gb"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"\n".join(sorted(words)) + b"\n")

        if len(words) != 127466:
            raise ValueError(f"unexpected words-gb entry count: {len(words)}")

    def package(self):
        copy(
            self,
            "words-gb",
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
        self.buildenv_info.define_path(
            "WORDS_GB_FILE",
            os.path.join(self.package_folder, "share", "dict", "words-gb"),
        )
        self.runenv_info.define_path(
            "WORDS_GB_FILE",
            os.path.join(self.package_folder, "share", "dict", "words-gb"),
        )
