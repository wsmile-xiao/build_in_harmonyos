#!/usr/bin/env python3
"""Consumer tests for tal 1.9 (all of them run the packaged bin/tal).

1. HarmonyOS PC consumer use case (tal_consumer): tal formats a generated
   C header inside a build pipeline, the OHOS toolchain compiles a program
   against the formatted header, and the program is run.  The header has a
   3000-column line: OHOS musl has LINE_MAX 4096, and tal reads input in
   LINE_MAX chunks, so a build with a 2048 limit splits that line, which
   breaks the macro continuation and the consumer no longer compiles.
2. test_tal.sh: the upstream example vectors and CLI behaviour.
"""
import os
import platform
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout

TABLE_ENTRIES = 1200
BLOB_AT = 600
BLOB_COLUMNS = 3000


def write_error_table(path):
    """Write a ragged X-macro header; return the values tal must preserve."""
    lines = ["#define ERROR_TABLE(X)"]
    total = 0
    blob_len = 0
    for i in range(1, TABLE_ENTRIES + 1):
        if i == BLOB_AT:
            head, tail = '    X(E_BLOB, sizeof("', '") - 1)'
            blob_len = BLOB_COLUMNS - len(head) - len(tail)
            lines.append(head + "x" * blob_len + tail)
            total += blob_len
        else:
            value = i * 31 % 1000
            lines.append(f"    X(E_ENTRY_{i}, {value})")
            total += value
    with open(path, "w", encoding="ascii") as out:
        for n, text in enumerate(lines):
            out.write(text + " " * (n % 5 + 1) + "\\\n")
        out.write("    /* end of ERROR_TABLE */\n")
    return {
        "EXPECTED_COUNT": TABLE_ENTRIES,
        "EXPECTED_SUM": total,
        "EXPECTED_BLOB": blob_len,
        "EXPECTED_CONTINUATIONS": len(lines),
        "EXPECTED_MIN_COLUMN": BLOB_COLUMNS,
    }


class TalTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _tal(self):
        folder = self.dependencies[self.tested_reference_str].package_folder
        return os.path.join(folder, "bin", "tal")

    def _aarch64_cmd(self, *args):
        """Run an AArch64 executable natively, or through qemu-aarch64."""
        if platform.machine().lower() in ("aarch64", "arm64"):
            return shlex.join(args)
        qemu = shutil.which("qemu-aarch64")
        if qemu is None:
            raise ConanException("qemu-aarch64 is required to run AArch64 binaries here")
        return shlex.join((qemu,) + args)

    def build(self):
        gen_dir = os.path.join(self.build_folder, "gen")
        os.makedirs(gen_dir, exist_ok=True)
        ragged = os.path.join(gen_dir, "error_table.h.in")
        aligned = os.path.join(gen_dir, "error_table.h")
        expected = write_error_table(ragged)
        # Step 2 of the consumer pipeline: the packaged tal formats the header.
        self.run(self._aarch64_cmd(self._tal(), ragged, aligned))
        cmake = CMake(self)
        cmake.configure(variables=dict(expected, TAL_GEN_DIR=gen_dir))
        # E074/E525: no FIFO jobserver on HMDFS, keep make serial.
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        consumer = os.path.join(self.cpp.build.bindir, "tal_consumer")
        header = os.path.join(self.build_folder, "gen", "error_table.h")
        self.run(self._aarch64_cmd(consumer, header), env="conanrun")
        script = os.path.join(self.recipe_folder, "test_tal.sh")
        self.run(shlex.join(["bash", script, self._tal()]), env="conanrun")
