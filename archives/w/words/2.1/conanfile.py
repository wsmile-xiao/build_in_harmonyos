#!/usr/bin/env python3
"""Conan recipe for the platform-independent words 2.1 dictionary data."""

import shutil
from pathlib import Path

from conan import ConanFile
from conan.tools.files import get
from conan.tools.layout import basic_layout


class WordsConan(ConanFile):
    name = "words"
    version = "2.1"
    description = "International UTF-8 word lists derived from GNU Aspell dictionaries"
    license = "GPL-2.0-only LicenseRef-Ispell LicenseRef-SCOWL"
    homepage = "https://ftp.gnu.org/gnu/aspell/dict/0index.html"
    url = "https://gitlab.archlinux.org/archlinux/packaging/packages/words"

    package_type = "unknown"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def source(self):
        for source in self.conan_data["sources"]:
            destination = Path(self.source_folder) / source["id"]
            destination.mkdir(parents=True, exist_ok=True)
            get(
                self,
                url=source["url"],
                sha256=source["sha256"],
                filename=source["filename"],
                destination=str(destination),
                strip_root=True,
            )

    @staticmethod
    def _decode_prezip_v1(data, source_name):
        """Decode Aspell's original prefix-delta format (header byte 1)."""
        offset = 1
        prefix_code = data[0]
        previous = b""
        previous_length = 0
        words = []

        while True:
            if prefix_code == 0:
                if offset >= len(data):
                    raise ValueError(f"{source_name} ends inside a v1 prefix escape")
                prefix_code = data[offset]
                offset += 1

            prefix_length = prefix_code - 1
            if prefix_length < 0 or prefix_length > previous_length:
                raise ValueError(f"{source_name} has an invalid v1 prefix length")

            current = bytearray(previous[:prefix_length])
            next_prefix = None
            while offset < len(data) and data[offset] > 32:
                current.append(data[offset])
                offset += 1
            if offset < len(data):
                next_prefix = data[offset]
                offset += 1

            word = bytes(current)
            words.append(word)
            previous = word
            previous_length = len(word)
            if next_prefix is None:
                break
            prefix_code = next_prefix

        return words

    @staticmethod
    def _decode_prezip_v2(data, source_name):
        """Decode Aspell's escaped prefix-delta format (header byte 2)."""
        offset = 1
        previous = b""
        words = []

        while offset < len(data):
            if data[offset] == 31 and offset + 1 < len(data) and data[offset + 1] == 255:
                offset += 2
                if offset != len(data):
                    raise ValueError(f"{source_name} has data after its v2 terminator")
                break

            prefix_code = data[offset]
            offset += 1
            if prefix_code < 30:
                prefix_length = prefix_code
            elif prefix_code == 30:
                prefix_length = 30
                while offset < len(data) and data[offset] == 255:
                    prefix_length += 255
                    offset += 1
                if offset >= len(data):
                    raise ValueError(f"{source_name} has a truncated v2 prefix")
                prefix_length += data[offset]
                offset += 1
            else:
                raise ValueError(f"{source_name} has an invalid v2 prefix control byte")

            if prefix_length > len(previous):
                raise ValueError(f"{source_name} references beyond its previous word")

            encoded = bytearray(previous[:prefix_length])
            while offset < len(data):
                if data[offset] == 31 and offset + 1 < len(data) and data[offset + 1] == 255:
                    break
                if data[offset] <= 30:
                    break
                encoded.append(data[offset])
                offset += 1

            decoded = bytearray()
            index = 0
            while index < len(encoded):
                if encoded[index] == 31:
                    if index + 1 >= len(encoded) or not 32 <= encoded[index + 1] < 64:
                        raise ValueError(f"{source_name} has an invalid v2 escape sequence")
                    decoded.append(encoded[index + 1] - 32)
                    index += 2
                else:
                    decoded.append(encoded[index])
                    index += 1

            word = bytes(decoded)
            words.append(word)
            previous = bytes(encoded)

        return words

    @classmethod
    def _decode_cwl(cls, path):
        data = Path(path).read_bytes()
        source_name = str(path)
        if not data:
            raise ValueError(f"{source_name} is empty")
        if data[0] == 1:
            return cls._decode_prezip_v1(data, source_name)
        if data[0] == 2:
            return cls._decode_prezip_v2(data, source_name)
        raise ValueError(f"{source_name} is not a supported Aspell prezip word list")

    @staticmethod
    def _sort_key(word):
        """Match LC_ALL=C sort -df, whose final tie-break is bytewise."""
        encoded = word.encode("utf-8")
        primary = bytes(
            byte + 32 if 65 <= byte <= 90 else byte
            for byte in encoded
            if byte in b" abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        )
        return primary, encoded

    @classmethod
    def _read_dictionary(cls, paths):
        words = []
        for path in paths:
            for encoded_word in cls._decode_cwl(path):
                # Arch's pipeline uses iconv ISO-8859-1 followed by cut at '/'.
                word = encoded_word.decode("latin-1").split("/", 1)[0]
                if word:
                    words.append(word)
        return words

    @classmethod
    def _write_dictionary(cls, destination, words, *, unique=False):
        if unique:
            words = set(words)
        ordered = sorted(words, key=cls._sort_key)
        Path(destination).parent.mkdir(parents=True, exist_ok=True)
        Path(destination).write_bytes(("\n".join(ordered) + "\n").encode("utf-8"))

    @staticmethod
    def _one_file(directory, name):
        matches = sorted(Path(directory).glob(name))
        if len(matches) != 1:
            raise ValueError(f"expected one {name} in {directory}, found {len(matches)}")
        return matches[0]

    def build(self):
        source_root = Path(self.source_folder)
        output_root = Path(self.build_folder) / "words-output"
        dictionary_dir = output_root / "share" / "dict"

        english_dir = source_root / "en"
        common = self._one_file(english_dir, "en-common.cwl")
        us = sorted(english_dir.glob("en_US*.cwl"))
        gb = sorted(english_dir.glob("en_GB*.cwl"))
        if len(us) != 2 or len(gb) != 6:
            raise ValueError(f"unexpected English dictionary inputs: en_US={len(us)}, en_GB={len(gb)}")
        self._write_dictionary(dictionary_dir / "american-english", self._read_dictionary([common, *us]), unique=True)
        self._write_dictionary(dictionary_dir / "british-english", self._read_dictionary([common, *gb]), unique=True)

        german_dir = source_root / "de"
        german = [self._one_file(german_dir, "de-only.cwl"), *sorted(german_dir.glob("de_*.cwl"))]
        if len(german) != 3:
            raise ValueError(f"unexpected German dictionary inputs: {len(german)}")

        standalone = {
            "catala": self._one_file(source_root / "ca", "ca-common.cwl"),
            "finnish": self._one_file(source_root / "fi", "fi.cwl"),
            "french": self._one_file(source_root / "fr", "fr-40-only.cwl"),
            "italian": self._one_file(source_root / "it", "it.cwl"),
            "ngerman": german,
            "ogerman": self._one_file(source_root / "de-alt", "de-alt.cwl"),
            "spanish": self._one_file(source_root / "es", "es.cwl"),
        }
        for name, paths in standalone.items():
            if not isinstance(paths, (list, tuple)):
                paths = [paths]
            self._write_dictionary(dictionary_dir / name, self._read_dictionary(paths), unique=name == "ngerman")

        aliases = {
            "british": "british-english",
            "catalan": "catala",
            "german": "ngerman",
            "usa": "american-english",
        }
        for alias, canonical in aliases.items():
            shutil.copyfile(dictionary_dir / canonical, dictionary_dir / alias)

        copyright_inputs = [
            ("en", "Copyright", "copyright-en"),
            ("ca", "Copyright", "copyright-ca"),
            ("fi", "Copyright", "copyright-fi"),
            ("fr", "Copyright", "copyright-fr"),
            ("it", "Copyright", "copyright-it"),
            ("de", "Copyright", "copyright-de"),
            ("de", "doc/Copyright", "copyright-de-doc"),
            ("es", "Copyright", "copyright-es"),
        ]
        license_dir = output_root / "licenses"
        license_dir.mkdir(parents=True, exist_ok=True)
        for source_id, relative, output_name in copyright_inputs:
            source_file = source_root / source_id / relative
            if not source_file.is_file():
                raise ValueError(f"missing upstream license file: {source_file}")
            shutil.copyfile(source_file, license_dir / output_name)

    def package(self):
        shutil.copytree(
            Path(self.build_folder) / "words-output" / "share",
            Path(self.package_folder) / "share",
            dirs_exist_ok=True,
        )
        shutil.copytree(
            Path(self.build_folder) / "words-output" / "licenses",
            Path(self.package_folder) / "licenses",
            dirs_exist_ok=True,
        )

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = ["share"]
        self.runenv_info.define_path("WORDS_DIR", str(Path(self.package_folder) / "share" / "dict"))
        self.buildenv_info.define_path("WORDS_DIR", str(Path(self.package_folder) / "share" / "dict"))
