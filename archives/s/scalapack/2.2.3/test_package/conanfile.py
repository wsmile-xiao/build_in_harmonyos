#!/usr/bin/env python3
"""Conan test_package for ScaLAPACK 2.2.3."""

import os
import re
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class ScalapackTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _find_ohos_tool(self, name):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler_dir = os.path.dirname(executables.get("c", ""))
        candidates = (
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        )
        return next((path for path in candidates if os.path.isfile(path)), "")

    def _sign_executable(self, path):
        if str(self.settings.os) != "OHOS":
            return
        objcopy = self._find_ohos_tool("llvm-objcopy")
        readelf = self._find_ohos_tool("llvm-readelf")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not readelf or not signer:
            raise ConanInvalidConfiguration(
                "OHOS consumer execution requires llvm-objcopy, llvm-readelf, "
                "and binary-sign-tool"
            )
        original_mode = os.stat(path).st_mode
        temporary = "{}.signing".format(path)
        try:
            shutil.copy2(path, temporary)
            self.run(
                '"{}" --remove-section .codesign "{}"'.format(
                    objcopy, temporary
                )
            )
            self.run(
                '"{}" sign -inFile "{}" -outFile "{}" -selfSign 1'.format(
                    signer, temporary, temporary
                )
            )
            os.chmod(temporary, original_mode)
            self._verify_signed_elf(temporary, readelf)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

    @staticmethod
    def _is_loadable_elf(path):
        if not os.path.isfile(path) or os.path.islink(path):
            return False
        with open(path, "rb") as stream:
            header = stream.read(18)
        if len(header) < 18 or header[:4] != b"\x7fELF":
            return False
        byteorder = "little" if header[5] == 1 else "big"
        return int.from_bytes(header[16:18], byteorder=byteorder) in (2, 3)

    def _verify_signed_elf(self, path, readelf):
        if not self._is_loadable_elf(path):
            raise ConanInvalidConfiguration(
                "signed consumer is not an ET_EXEC or ET_DYN ELF"
            )
        completed = subprocess.run(
            [readelf, "-SW", path],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        sections = re.findall(
            r"^\s*\[\s*\d+\]\s+\.codesign\s+(\S+)\s+"
            r"[0-9A-Fa-f]+\s+[0-9A-Fa-f]+\s+([0-9A-Fa-f]+)\b",
            completed.stdout,
            re.MULTILINE,
        )
        if (
            completed.returncode != 0
            or len(sections) != 1
            or sections[0][0] != "PROGBITS"
            or int(sections[0][1], 16) == 0
        ):
            raise ConanInvalidConfiguration(
                "signed consumer must contain exactly one non-empty PROGBITS "
                ".codesign section"
            )

    def _mpi_launcher(self):
        launchers = []
        for dependency in self.dependencies.host.values():
            package_folder = dependency.package_folder
            if not package_folder:
                continue
            for name in ("mpiexec", "mpirun"):
                candidate = os.path.join(package_folder, "bin", name)
                if os.path.isfile(candidate):
                    launchers.append(candidate)
                    break
        if len(launchers) != 1:
            raise ConanInvalidConfiguration(
                "Expected exactly one packaged MPI launcher, found: {}".format(
                    ", ".join(launchers) if launchers else "none"
                )
            )
        return launchers[0]

    def test(self):
        if cross_building(self):
            self.output.info("Cross-building: compile and link probe completed")
            return
        launcher = self._mpi_launcher()
        executable = os.path.join(self.cpp.build.bindir, "test_scalapack")
        self._sign_executable(executable)
        command = "{} -n 2 {}".format(
            shlex.quote(launcher), shlex.quote(executable)
        )
        self.run(command, env="conanrun")
