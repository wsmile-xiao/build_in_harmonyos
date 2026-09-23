#!/usr/bin/env python3
"""Conan consumer test for liblemon 1.3.1."""

import os
import shlex
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import cross_building


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dependency = self.dependencies["liblemon"]
        flags = []
        flags.extend(f"-I{path}" for path in dependency.cpp_info.includedirs)
        flags.extend(f"-L{path}" for path in dependency.cpp_info.libdirs)
        flags.extend(f"-l{name}" for name in dependency.cpp_info.libs)
        flags.extend(f"-l{name}" for name in dependency.cpp_info.system_libs)
        if str(self.settings.os) != "Windows" and dependency.cpp_info.libdirs:
            flags.append(f"-Wl,-rpath,{dependency.cpp_info.libdirs[0]}")
        command = [
            self._cxx_compiler(),
            "test.cpp",
            "-o",
            "liblemon_test",
            *dict.fromkeys(flags),
        ]
        self.run(self._serialize(command))
        if str(self.settings.os) == "OHOS":
            self._sign_elf(Path(self.build_folder, "liblemon_test"))

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile and link only")
            return
        self.run("./liblemon_test", env="conanrun")

    def _sign_elf(self, executable):
        if not executable.is_file():
            raise ConanInvalidConfiguration(
                f"required OHOS consumer ELF is missing: {executable}"
            )
        objcopy = self._resolve_tool("objcopy")
        try:
            readelf = self._resolve_tool("readelf")
        except ConanInvalidConfiguration:
            readelf = self._resolve_tool("readobj")
        signer = self._resolve_tool("binary-sign-tool", llvm=False)
        temporary = executable.with_name(f"{executable.name}.signing-{os.getpid()}")
        try:
            shutil.copy2(executable, temporary)
            sections = self._read_sections(readelf, temporary)
            if ".codesign" in sections:
                subprocess.run(
                    [objcopy, "--remove-section", ".codesign", str(temporary)],
                    check=True,
                )
            subprocess.run(
                [
                    signer,
                    "sign",
                    "-inFile",
                    str(temporary),
                    "-outFile",
                    str(temporary),
                    "-selfSign",
                    "1",
                ],
                check=True,
            )
            signed_sections = self._read_sections(readelf, temporary)
            if ".codesign" not in signed_sections:
                raise ConanException(
                    f"signer did not add .codesign: {executable}"
                )
            os.replace(temporary, executable)
        finally:
            if temporary.exists():
                temporary.unlink()

    def _read_sections(self, readelf, executable):
        if str(self.settings.os) == "OHOS" and Path(readelf).name in {
            "llvm-readobj",
            "llvm-readobj.exe",
        }:
            command = [readelf, "--sections", str(executable)]
        else:
            command = [readelf, "-S", str(executable)]
        return subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        ).stdout

    def _resolve_tool(self, tool, llvm=True):
        compiler = self._cxx_compiler()
        compiler_dir = os.path.dirname(compiler)
        compiler_name = os.path.basename(compiler)
        suffix = (
            compiler_name[len("clang++") :]
            if compiler_name.startswith("clang++")
            else ""
        )
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        candidates = [executables.get(tool)]
        if compiler_dir:
            if llvm:
                candidates.extend(
                    [
                        os.path.join(compiler_dir, f"llvm-{tool}{suffix}"),
                        os.path.join(compiler_dir, f"llvm-{tool}"),
                    ]
                )
            candidates.append(os.path.join(compiler_dir, tool))
        if llvm and suffix:
            candidates.append(f"llvm-{tool}{suffix}")
        if llvm:
            candidates.append(f"llvm-{tool}")
        candidates.append(tool)
        for candidate in candidates:
            if candidate:
                resolved = shutil.which(candidate)
                if resolved:
                    return resolved
        raise ConanInvalidConfiguration(f"required OHOS tool was not found: {tool}")

    def _cxx_compiler(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = executables.get("cpp") or shutil.which("c++")
        resolved = shutil.which(compiler) if compiler else None
        if not resolved:
            raise ConanInvalidConfiguration("No C++ compiler is configured")
        return resolved

    def _serialize(self, command):
        if str(self.settings.os) == "Windows":
            return subprocess.list2cmdline([str(item) for item in command])
        return shlex.join(str(item) for item in command)
