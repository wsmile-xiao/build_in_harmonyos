#!/usr/bin/env python3
"""Consumer and HarmonyOS-native test_package for wmfsm 0.36."""

import json
import os
import shlex
import struct

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.layout import basic_layout

SCRIPT_CHECKS = 3
EM_AARCH64 = 183


class WmfsmTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        if not can_run(self):
            raise ConanException("wmfsm test_package must run on the OHOS host")
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanException("the consumer test requires native OHOS armv8")

        package = self.dependencies["wmfsm"]
        binary = os.path.join(package.package_folder, "bin", "wmfsm")
        script = os.path.join(self.recipe_folder, "test_wmfsm.sh")
        shim_source = os.path.join(self.recipe_folder, "mount_fallback_shim.c")
        if not os.path.isfile(binary):
            raise ConanException("packaged wmfsm binary is missing: " + binary)
        if not os.path.isfile(script) or not os.path.isfile(shim_source):
            raise ConanException("wmfsm consumer test sources are incomplete")

        scratch = os.path.join(self.build_folder, "scratch")
        os.makedirs(scratch, exist_ok=True)
        shim = os.path.join(scratch, "mount_fallback_shim.so")
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict)
        compiler = compiler_executables.get("c")
        if not compiler:
            raise ConanException(
                "tools.build:compiler_executables must configure the C compiler")
        compile_command = "{} -shared -fPIC {} -ldl -o {}".format(
            shlex.quote(compiler), shlex.quote(shim_source), shlex.quote(shim))
        self.run(compile_command, cwd=scratch, env="conanbuild")

        self.run("bash {} {} {} {}".format(
            shlex.quote(script), shlex.quote(binary), shlex.quote(shim),
            shlex.quote(scratch)), cwd=scratch, env="conanrun")

        script_count = self._read_script_count(
            os.path.join(scratch, "checks.count"))
        if script_count != SCRIPT_CHECKS:
            raise ConanException(
                "test script reported {} checks; expected {}".format(
                    script_count, SCRIPT_CHECKS))

        self._check_elf(binary)
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "packaged CLI checks + OHOS /proc/mounts parsing and successful statfs",
            "consumer_passed": SCRIPT_CHECKS,
            "consumer_total": SCRIPT_CHECKS,
        }, sort_keys=True))

    @staticmethod
    def _read_script_count(path):
        if not os.path.isfile(path):
            raise ConanException("test script did not report its check count")
        with open(path, "r", encoding="utf-8") as handle:
            return int(handle.read().strip())

    def _check_elf(self, binary):
        with open(binary, "rb") as handle:
            header = handle.read(20)
        if len(header) != 20 or header[:4] != b"\x7fELF":
            raise ConanException("packaged wmfsm is not an ELF executable")
        if header[4] != 2 or header[5] != 1:
            raise ConanException("packaged wmfsm is not little-endian ELF64")
        machine = struct.unpack_from("<H", header, 18)[0]
        if machine != EM_AARCH64:
            raise ConanException(
                "packaged wmfsm ELF machine is {}, expected AArch64".format(
                    machine))

        self.output.info("OK: package binary is little-endian ELF64/AArch64")
        self.output.info("OK: Conan test host is HarmonyOS OHOS/armv8")
