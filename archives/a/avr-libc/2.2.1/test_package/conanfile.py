#!/usr/bin/env python3
"""Consumer test for the AVR target artifacts in avr-libc."""

import os
import re
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration


class AvrLibcTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv"
    test_type = "explicit"
    exports_sources = "test_avr_libc.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        self.tool_requires("avr-binutils/2.43.1")
        self.tool_requires("avr-gcc-bootstrap/14.2.0")

    def test(self):
        package_folder = self.dependencies["avr-libc"].package_folder
        avr_root = os.path.join(package_folder, "avr")
        include_dir = os.path.join(avr_root, "include")
        compiler = self._required_build_tool("avr-gcc")
        lib_dir = self._atmega328p_libdir(avr_root, compiler)
        objdump = self._required_build_tool("avr-objdump")
        nm = self._required_build_tool("avr-nm")

        crt = os.path.join(lib_dir, "crtatmega328p.o")
        libc = os.path.join(lib_dir, "libc.a")
        libm = os.path.join(lib_dir, "libm.a")
        device = os.path.join(lib_dir, "libatmega328p.a")
        for artifact in (crt, libc, libm, device):
            if not os.path.isfile(artifact):
                raise ConanInvalidConfiguration(
                    "Required tested-package artifact is missing: {}".format(artifact)
                )

        source = os.path.join(self.source_folder, "test_avr_libc.c")
        elf = os.path.join(self.build_folder, "test_avr_libc.elf")
        map_file = os.path.join(self.build_folder, "test_avr_libc.map")
        command = [
            compiler,
            "-mmcu=atmega328p",
            "-Os",
            "-fno-builtin",
            "-I{}".format(include_dir),
            "-nostdlib",
            crt,
            source,
            "-Wl,-Map,{}".format(map_file),
            "-Wl,--start-group",
            libc,
            libm,
            device,
            "-lgcc",
            "-Wl,--end-group",
            "-o",
            elf,
        ]
        self.run(" ".join(shlex.quote(item) for item in command), env="conanbuild")

        objdump_report = os.path.join(self.build_folder, "objdump.txt")
        nm_report = os.path.join(self.build_folder, "nm.txt")
        self.run(
            '{} -f {} > {}'.format(
                shlex.quote(objdump), shlex.quote(elf), shlex.quote(objdump_report)
            ),
            env="conanbuild",
        )
        self.run(
            '{} -g {} > {}'.format(
                shlex.quote(nm), shlex.quote(elf), shlex.quote(nm_report)
            ),
            env="conanbuild",
        )

        with open(objdump_report, encoding="utf-8", errors="replace") as handle:
            objdump_text = handle.read()
        if "architecture: avr" not in objdump_text:
            raise ConanInvalidConfiguration("Consumer output is not an AVR ELF")

        with open(nm_report, encoding="utf-8", errors="replace") as handle:
            symbols = handle.read()
        for symbol in ("memcpy", "strlen", "sin"):
            if not re.search(r"\bT\s+{}$".format(symbol), symbols, re.MULTILINE):
                raise ConanInvalidConfiguration(
                    "Linked AVR ELF does not contain tested avr-libc symbol: {}".format(symbol)
                )

        self.output.info("avr-libc consumer compile/link test passed for ATmega328P")

    def _atmega328p_libdir(self, avr_root, compiler):
        report = os.path.join(self.build_folder, "multidir.txt")
        self.run(
            '{} -mmcu=atmega328p -print-multi-directory > {}'.format(
                shlex.quote(compiler), shlex.quote(report)
            ),
            env="conanbuild",
        )
        with open(report, encoding="utf-8", errors="replace") as handle:
            multidir = handle.read().strip()
        if not multidir or os.path.isabs(multidir):
            raise ConanInvalidConfiguration(
                "avr-gcc returned an invalid ATmega328P multilib path: {!r}".format(
                    multidir
                )
            )

        lib_root = os.path.realpath(os.path.join(avr_root, "lib"))
        lib_dir = os.path.realpath(os.path.join(lib_root, multidir))
        if lib_dir != lib_root and not lib_dir.startswith(lib_root + os.sep):
            raise ConanInvalidConfiguration(
                "avr-gcc multilib path escapes the tested package: {}".format(multidir)
            )
        return lib_dir

    def _required_build_tool(self, executable):
        for dependency in self.dependencies.build.values():
            package_folder = dependency.package_folder
            if not package_folder:
                continue
            for bindir in dependency.cpp_info.bindirs or []:
                root = bindir if os.path.isabs(bindir) else os.path.join(package_folder, bindir)
                candidate = os.path.join(root, executable)
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    return candidate
        raise ConanInvalidConfiguration(
            "Required AVR test tool '{}' was not provided by tool_requires".format(executable)
        )
