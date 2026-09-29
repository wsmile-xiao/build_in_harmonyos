#!/usr/bin/env python3
"""Conan recipe — undms 1.3 (single-file C source, generated CMake project).

Upstream ships only undms.c compressed with Unix compress(1) (.c.Z, LZW);
source() decodes it in pure Python, so no gzip/uncompress is needed on the
OHOS device, and build() compiles a static CLI through CMakeToolchain.
"""
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, download, export_conandata_patches


def _unlzw(data):
    """Read Unix compress(1) LZW (.Z); see knowledge draft E6417."""
    if len(data) < 3 or data[:2] != b"\x1f\x9d":
        raise ConanException("undms.c.Z: not a compress(1) stream")
    maxbits = data[2] & 0x1f
    block_mode = bool(data[2] & 0x80)
    if not 9 <= maxbits <= 16:
        raise ConanException("undms.c.Z: bad code width")
    maxmaxcode = 1 << maxbits
    total_bits = len(data) * 8
    pos = group = 24
    n_bits = 9
    maxcode = (1 << n_bits) - 1
    table = [bytes([i]) for i in range(256)] + [b""]
    free_ent = 257 if block_mode else 256
    out = bytearray()
    old = None
    while True:
        if free_ent > maxcode and n_bits < maxbits:
            span = n_bits * 8
            pos = group = group + -(-(pos - group) // span) * span
            n_bits += 1
            maxcode = maxmaxcode if n_bits == maxbits else (1 << n_bits) - 1
            continue
        if pos + n_bits > total_bits:
            break
        byte, bit = divmod(pos, 8)
        code = (int.from_bytes(data[byte:byte + 3], "little") >> bit) & ((1 << n_bits) - 1)
        pos += n_bits
        if old is None:
            if code >= 256:
                raise ConanException("undms.c.Z: corrupt first code")
            out += table[code]
            old = code
            continue
        if code == 256 and block_mode:
            span = n_bits * 8
            pos = group = group + -(-(pos - group) // span) * span
            del table[257:]
            free_ent = 256
            n_bits = 9
            maxcode = (1 << n_bits) - 1
            continue
        if code < len(table):
            entry = table[code]
        elif code == free_ent:
            entry = table[old] + table[old][:1]
        else:
            raise ConanException("undms.c.Z: corrupt code")
        out += entry
        if free_ent < maxmaxcode:
            new = table[old] + entry[:1]
            if free_ent < len(table):
                table[free_ent] = new
            else:
                table.append(new)
            free_ent += 1
        old = code
    return bytes(out)


class UndmsConan(ConanFile):
    name = "undms"
    version = "1.3"
    description = "DMS disk archive extractor"
    homepage = "https://aminet.net/package/misc/unix/undms-1.3.c"
    license = "unknown"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        data = self.conan_data["sources"][str(self.version)]
        archive = Path(self.source_folder) / "undms.c.Z"
        download(self, data["url"], str(archive), sha256=data["sha256"])
        (Path(self.source_folder) / "undms.c").write_bytes(_unlzw(archive.read_bytes()))

    def generate(self):
        CMakeToolchain(self).generate()

    def build(self):
        apply_conandata_patches(self)
        src = Path(self.build_folder) / "undms-src"
        src.mkdir(parents=True, exist_ok=True)
        copy(self, "undms.c", self.source_folder, str(src))
        (src / "CMakeLists.txt").write_text(
            "cmake_minimum_required(VERSION 3.15)\n"
            "project(undms C)\n"
            "add_executable(undms undms.c)\n"
            "target_link_options(undms PRIVATE -static)\n"
            "install(TARGETS undms RUNTIME DESTINATION bin)\n",
            encoding="utf-8",
        )
        cmake = CMake(self)
        cmake.configure(build_script_folder=str(src))
        cmake.build()

    def package(self):
        CMake(self).install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
