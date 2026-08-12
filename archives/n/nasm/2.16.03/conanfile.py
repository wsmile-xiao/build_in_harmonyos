#!/usr/bin/env python3
"""Conan recipe for NASM 2.16.03."""

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import load_toolchain_args
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class NasmConan(ConanFile):
    name = "nasm"
    version = "2.16.03"
    description = "Netwide Assembler, a portable x86 assembler and disassembler"
    license = "BSD-2-Clause"
    homepage = "https://www.nasm.us/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("NASM is adapted for Linux and OHOS")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        toolchain = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            triplet = self._ohos_triplet()
            toolchain.configure_args.extend(
                [f"--build={triplet}", f"--host={triplet}"]
            )
            environment = toolchain.environment()
            shell = self._config_shell()
            environment.define("CONFIG_SHELL", shell)
            environment.define("SHELL", shell)
            toolchain.generate(env=environment)
        else:
            toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        os.chmod(os.path.join(self.source_folder, "configure"), 0o755)
        autotools = Autotools(self)
        if str(self.settings.os) == "OHOS":
            self._configure_with_shell()
        else:
            autotools.configure()
        autotools.make(args=["-j1"])
        self._smoke_test_build_output()

    def package(self):
        Autotools(self).install(args=["-j1"])
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.buildenv_info.prepend_path("PATH", bin_dir)
        self.runenv_info.prepend_path("PATH", bin_dir)
        self.buildenv_info.define_path("NASM", os.path.join(bin_dir, "nasm"))
        self.runenv_info.define_path("NASM", os.path.join(bin_dir, "nasm"))

    def _smoke_test_build_output(self):
        source = os.path.join(self.build_folder, "conan-smoke.asm")
        output = os.path.join(self.build_folder, "conan-smoke.bin")
        save(
            self,
            source,
            "bits 16\n"
            "org 0x100\n"
            "mov ax, 0x1234\n"
            "add ax, byte 1\n"
            "ret\n",
        )
        nasm = os.path.join(self.build_folder, "nasm")
        self._run_native(
            f"{shlex.quote(nasm)} -f bin "
            f"{shlex.quote(source)} -o {shlex.quote(output)}"
        )
        with open(output, "rb") as handle:
            machine_code = handle.read()
        expected = bytes.fromhex("b8341283c001c3")
        if machine_code != expected:
            raise ConanException(
                f"NASM smoke output mismatch: {machine_code.hex()} != {expected.hex()}"
            )

    def _run_native(self, command):
        shell = self._config_shell()
        self.run(
            f"{shlex.quote(shell)} -c {shlex.quote(command)}",
            env="conanautotoolstoolchain",
        )

    def _configure_with_shell(self):
        configure_args = load_toolchain_args(self.generators_folder).get(
            "configure_args", ""
        )
        shell = self._config_shell()
        configure = os.path.join(self.source_folder, "configure")
        command = " ".join(
            part
            for part in (
                f"CONFIG_SHELL={shlex.quote(shell)}",
                f"SHELL={shlex.quote(shell)}",
                shlex.quote(shell),
                shlex.quote(configure),
                configure_args,
            )
            if part
        )
        self.run(command, cwd=self.build_folder, env="conanbuild")

    @staticmethod
    def _config_shell():
        for candidate in (
            os.environ.get("CONFIG_SHELL"),
            "/data/service/hnp/bin/bash",
            shutil.which("bash"),
            shutil.which("sh"),
            "/system/bin/sh",
            "/bin/sh",
        ):
            if not candidate:
                continue
            if os.path.isabs(candidate):
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    return candidate
            elif shutil.which(candidate):
                return candidate
        return "sh"

    def _ohos_triplet(self):
        cpu = {
            "armv8": "aarch64",
            "armv8.3": "aarch64",
            "armv8_32": "arm",
            "armv7": "arm",
            "x86_64": "x86_64",
        }.get(str(self.settings.arch), str(self.settings.arch))
        return f"{cpu}-unknown-linux-ohos"
