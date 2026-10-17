#!/usr/bin/env python3
"""Consumer test for the packaged lib32-gcc 32-bit ARM (arm-linux-ohos) cross-compiler.

This is the HarmonyOS-specific consumer use case required by the PC PR review
rules: ONE complete end-to-end flow driven by the *installed* Conan package --
not a handful of isolated assertions on a single file.  Every stage below is
performed by the packaged toolchain that the consumer actually receives:

    stage 1  driver identity      gcc --version
    stage 2  target identity      gcc -dumpmachine
    stage 3  preprocess           gcc -E  (OHOS target macro must be visible)
    stage 4  compile TU-A         gcc -c  consumer_lib.c
    stage 5  compile TU-B         gcc -c  consumer_main.c
    stage 6  link                 gcc     consumer_main.o consumer_lib.o
    stage 7  inspect artifacts    llvm-readelf (ELF class/machine/type,
                                  entry point, cross-TU symbol resolution,
                                  .ARM.attributes assembler fingerprint)
    stage 8  target ABI program   gcc -DEXPECT_OHOS=1 test_gcc.c

TU-A compiles the library code, TU-B compiles a *different* translation unit
that only declares those functions, and the link step is what proves the
packaged assembler and the device GNU ld actually resolved the cross-TU
references -- an empty or stubbed package cannot produce that artifact.

arm-linux-ohos output is a 32-bit ARM binary and cannot execute on the
aarch64 build host, so the linked program is validated structurally instead
of being run.  The 31 hard assertions this flow enforces (stage by stage) are
enumerated in MANIFEST.yml.
"""

import os
import re
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration


class Lib32GccTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = (
        "test_gcc.c",
        "consumer_lib.c",
        "consumer_lib.h",
        "consumer_main.c",
        "consumer_probe.c",
    )

    def config_options(self):
        self.settings.rm_safe("os.version")

    def requirements(self):
        self.requires(self.tested_reference_str)

    # -- packaged package layout -------------------------------------------

    @property
    def _bindir(self):
        bindirs = self.dependencies["lib32-gcc"].cpp_info.bindirs
        if not bindirs:
            raise ConanInvalidConfiguration(
                "The lib32-gcc package does not declare a binary directory"
            )
        return os.path.join(
            self.dependencies["lib32-gcc"].package_folder, bindirs[0]
        )

    @property
    def _gcc(self):
        executable = os.path.join(self._bindir, "gcc")
        if not os.path.isfile(executable):
            raise ConanInvalidConfiguration(
                "The packaged lib32-gcc executable was not found: {}".format(executable)
            )
        return executable

    @property
    def _gcc_command(self):
        # OHOS /system/bin/sh cannot exec ELF binaries directly, and the
        # packaged driver is itself a /bin/sh wrapper, so drive it through an
        # explicit shell (same spelling the build-time torture runner uses).
        command = shlex.quote(self._gcc)
        if str(self.settings.os) == "OHOS":
            return "sh {}".format(command)
        return command

    # -- small helpers -----------------------------------------------------

    def _source(self, name):
        return os.path.join(self.source_folder, name)

    def _artifact(self, name):
        return os.path.join(self.build_folder, name)

    def _capture(self, command):
        """Run the packaged driver and return its stdout."""
        return subprocess.run(
            command, shell=True, capture_output=True, text=True, check=True
        ).stdout

    @staticmethod
    def _find_tool(names):
        for name in names:
            candidate = shutil.which(name) or name
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _require(self, condition, message):
        if not condition:
            raise ConanInvalidConfiguration(message)

    def _readelf(self, *arguments):
        readelf = self._find_tool(
            ["llvm-readelf", "readelf", "/data/service/hnp/bin/llvm-readelf"]
        )
        if not readelf:
            raise ConanInvalidConfiguration(
                "llvm-readelf is required to validate the ARM32 artifacts"
            )
        return subprocess.run(
            [readelf] + list(arguments),
            capture_output=True,
            text=True,
            check=True,
        ).stdout

    def _expect_elf(self, path, note):
        """Validate ELF class, machine and non-emptiness; return the header."""
        header = self._readelf("-h", path)
        self._require(
            re.search(r"Class:\s+ELF32\b", header) is not None,
            "{}: {} is not a 32-bit ELF".format(note, path),
        )
        self._require(
            re.search(r"Machine:\s+ARM\b", header) is not None,
            "{}: {} is not an ARM object".format(note, path),
        )
        self._require(
            os.path.getsize(path) > 0,
            "{}: {} is empty".format(note, path),
        )
        return header

    @staticmethod
    def _symbol_entry(symtab, symbol):
        """Return {"type", "ndx"} for ``symbol`` in a llvm-readelf -s listing."""
        for raw in symtab.splitlines():
            parts = raw.strip().split()
            if len(parts) < 8 or not parts[0].endswith(":"):
                continue
            if parts[-1] != symbol:
                continue
            # Num: Value Size Type Bind Vis Ndx Name
            return {"type": parts[3], "ndx": parts[6]}
        return None

    def _expect_symbol(self, symtab, symbol, defined, note, expect_type=None):
        entry = self._symbol_entry(symtab, symbol)
        self._require(
            entry is not None,
            "{}: symbol {} is missing from the symbol table".format(note, symbol),
        )
        is_defined = entry["ndx"] != "UND"
        self._require(
            is_defined == defined,
            "{}: symbol {} is {} but expected {}".format(
                note,
                symbol,
                "defined" if is_defined else "undefined",
                "defined" if defined else "undefined",
            ),
        )
        if expect_type is not None:
            self._require(
                entry["type"] == expect_type,
                "{}: symbol {} has type {} (expected {})".format(
                    note, symbol, entry["type"], expect_type
                ),
            )

    # -- stage 2: target identity -----------------------------------------

    def _expect_target(self):
        target = self._capture("{} -dumpmachine".format(self._gcc_command)).strip()
        self._require(
            target == "arm-linux-ohos",
            "lib32-gcc -dumpmachine reported {} (expected arm-linux-ohos)".format(target),
        )
        self.output.info("lib32-gcc target machine: {}".format(target))

    # -- flow --------------------------------------------------------------

    def build(self):
        # stage 1 -- the packaged driver really is a working GCC.
        version = self._capture("{} --version".format(self._gcc_command))
        self._require(
            "16.1" in version and version.strip() != "",
            "The packaged driver did not report a GCC 16.1.x version: {}".format(
                version.strip()[:120]
            ),
        )
        self.output.info("lib32-gcc driver: {}".format(version.splitlines()[0]))

        # stage 2 -- the driver targets 32-bit ARM OHOS.
        self._expect_target()

        # stage 3 -- preprocessing: the OHOS target macro injected by the
        # recipe (gcc/config/ohos.h appended to arm/linux-eabi.h) must already
        # be visible in the -E output.
        preprocessed = self._capture(
            "{} -E {}".format(
                self._gcc_command, shlex.quote(self._source("consumer_probe.c"))
            )
        )
        self._require(
            '"arm-linux-ohos-32bit-abi"' in preprocessed,
            "The OHOS target macro did not reach the preprocessor stage "
            "(consumer_lib.h CONSUMER_TARGET_ABI_MARKER was not expanded to the "
            "arm-linux-ohos marker)",
        )

        # stage 4 -- compile translation unit A (the library).
        library_object = self._artifact("consumer_lib.o")
        self.run(
            "{} -O2 -c {} -o {}".format(
                self._gcc_command,
                shlex.quote(self._source("consumer_lib.c")),
                shlex.quote(library_object),
            ),
            env="conanrun",
            ignore_errors=False,
        )
        library_header = self._expect_elf(library_object, "consumer_lib.o")
        self._require(
            re.search(r"Type:\s+REL\b", library_header) is not None,
            "consumer_lib.o is not a relocatable object (Type: REL)",
        )
        # The packaged GNU ARM gas is the only ARM assembler on OHOS; its
        # .ARM.attributes section is the assembler fingerprint of the object.
        self._require(
            ".ARM.attributes" in self._readelf("-S", library_object),
            "consumer_lib.o carries no .ARM.attributes section, so the packaged "
            "GNU ARM assembler did not produce it",
        )
        library_symtab = self._readelf("-s", library_object)
        self._expect_symbol(
            library_symtab,
            "consumer_compute",
            defined=True,
            note="consumer_lib.o",
            expect_type="FUNC",
        )

        # stage 5 -- compile translation unit B (the consumer program).
        main_object = self._artifact("consumer_main.o")
        self.run(
            "{} -O2 -c {} -o {}".format(
                self._gcc_command,
                shlex.quote(self._source("consumer_main.c")),
                shlex.quote(main_object),
            ),
            env="conanrun",
            ignore_errors=False,
        )
        self._expect_elf(main_object, "consumer_main.o")
        main_symtab = self._readelf("-s", main_object)
        self._expect_symbol(
            main_symtab,
            "consumer_compute",
            defined=False,
            note="consumer_main.o",
        )

        # stage 6 -- link the consumer program across both translation units.
        program = self._artifact("consumer_program")
        self.run(
            "{} -O2 {} {} -o {}".format(
                self._gcc_command,
                shlex.quote(main_object),
                shlex.quote(library_object),
                shlex.quote(program),
            ),
            env="conanrun",
            ignore_errors=False,
        )

        # stage 7 -- inspect the linked artifact.
        program_header = self._expect_elf(program, "consumer_program")
        self._require(
            re.search(r"Type:\s+(EXEC|DYN)\b", program_header) is not None,
            "consumer_program is not an executable ELF (Type: EXEC/DYN)",
        )
        entry = re.search(r"Entry point address:\s+0x([0-9a-fA-F]+)", program_header)
        self._require(
            entry is not None and int(entry.group(1), 16) != 0,
            "consumer_program has no entry point, so the arm-linux-ohos start "
            "files were not linked",
        )
        program_symtab = self._readelf("-s", program)
        self._expect_symbol(program_symtab, "main", defined=True, note="consumer_program")
        self._expect_symbol(
            program_symtab,
            "consumer_compute",
            defined=True,
            note="consumer_program",
            expect_type="FUNC",
        )
        self._expect_symbol(
            program_symtab,
            "consumer_target_abi",
            defined=True,
            note="consumer_program",
        )

        # stage 8 -- compile-time target ABI program: __OHOS__ must be defined
        # and the target ABI must be 32-bit (enforced by #error/_Static_assert
        # inside test_gcc.c, so a wrong target fails this compile).
        define = "-DEXPECT_OHOS=1" if str(self.settings.os) == "OHOS" else ""
        abi_program = self._artifact("gcc_test_program")
        self.run(
            "{} -O2 {} {} -o {}".format(
                self._gcc_command,
                define,
                shlex.quote(self._source("test_gcc.c")),
                shlex.quote(abi_program),
            ),
            env="conanrun",
            ignore_errors=False,
        )
        self._expect_elf(abi_program, "gcc_test_program")

        self.output.info(
            "HarmonyOS consumer end-to-end flow passed: preprocess -> compile "
            "TU-A/TU-B -> assemble (packaged GNU ARM gas) -> link (device GNU ld) "
            "-> validate ARM32/OHOS artifacts"
        )

    def test(self):
        for name in (
            "consumer_lib.o",
            "consumer_main.o",
            "consumer_program",
            "gcc_test_program",
        ):
            path = self._artifact(name)
            if not os.path.isfile(path):
                raise ConanInvalidConfiguration(
                    "The lib32-gcc consumer flow did not produce {}: {}".format(name, path)
                )
        self.output.info(
            "HarmonyOS consumer test passed: the packaged lib32-gcc cross-compiled "
            "a two-translation-unit consumer program to a valid 32-bit ARM "
            "(arm-linux-ohos) ELF, and __OHOS__ plus the 32-bit target ABI were "
            "enforced at compile time."
        )
