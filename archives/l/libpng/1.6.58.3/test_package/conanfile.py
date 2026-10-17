#!/usr/bin/env python3
"""Conan consumer test for libpng 1.6.58."""

import os
import shlex
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        libpng_dependency = self.dependencies["libpng"]
        dep = libpng_dependency.cpp_info
        incs = []
        libdirs = []
        libs = []
        ordered_dependencies = [libpng_dependency]
        ordered_dependencies.extend(
            dependency
            for _ref, dependency in self.dependencies.items()
            if dependency.ref.name != "libpng"
        )
        for _d in ordered_dependencies:
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
            libdirs += ["-L" + p for p in _d.cpp_info.libdirs]
            libs += ["-l" + lib for lib in _d.cpp_info.libs]
            libs += ["-l" + lib for lib in _d.cpp_info.system_libs]
        cc = self._c_compiler()
        flags = list(dict.fromkeys(incs + libdirs + libs))
        rpath = f"-Wl,-rpath,{dep.libdirs[0]}"
        command = [cc, "test.c", "-o", "test_probe", *flags, rpath]
        serialized = (
            subprocess.list2cmdline(command)
            if str(self.settings.os) == "Windows"
            else shlex.join(command)
        )
        self.run(serialized)
        if str(self.settings.os) == "OHOS":
            self._sign_elf(Path(self.build_folder, "test_probe"))

    def test(self):
        self._assert_metadata_aliases_removed(
            self.dependencies["libpng"].package_folder
        )
        if cross_building(self):
            self.output.info("cross-building: compile and link only")
            return
        self.run("./test_probe", env="conanrun")

    @staticmethod
    def _assert_metadata_aliases_removed(package_folder):
        for relative in ("bin/libpng-config", "lib/libpng.la"):
            path = Path(package_folder, relative)
            if path.exists() or path.is_symlink():
                raise ConanException(
                    f"removed metadata alias is still packaged: {relative}"
                )

    def _sign_elf(self, executable):
        if not executable.is_file():
            raise ConanInvalidConfiguration(
                f"required OHOS consumer ELF is missing: {executable}"
            )
        objcopy = self._resolve_tool("objcopy")
        readelf = self._resolve_tool("readelf")
        signer = self._resolve_tool("binary-sign-tool", llvm=False)
        temporary = executable.with_name(
            f"{executable.name}.signing-{os.getpid()}"
        )
        try:
            shutil.copy2(executable, temporary)
            sections = subprocess.run(
                [readelf, "-S", str(temporary)],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
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
            signed_sections = subprocess.run(
                [readelf, "-S", str(temporary)],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            if ".codesign" not in signed_sections:
                raise ConanException(f"signer did not add .codesign: {executable}")
            os.replace(temporary, executable)
        finally:
            if temporary.exists():
                temporary.unlink()

    def _resolve_tool(self, tool, llvm=True):
        compiler_path = self._c_compiler()
        compiler_dir = os.path.dirname(compiler_path)
        compiler_name = os.path.basename(compiler_path)
        suffix = (
            compiler_name[len("clang") :]
            if compiler_name.startswith("clang")
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

    def _c_compiler(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = executables.get("c") or shutil.which("cc")
        resolved = shutil.which(compiler) if compiler else None
        if not resolved:
            raise ConanInvalidConfiguration("No C compiler is configured")
        return resolved
