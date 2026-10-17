#!/usr/bin/env python3
"""Consumer tests for SDL2 2.32.10."""

import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class SDL2TestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "VirtualRunEnv"
    test_type = "explicit"

    _binary_names = (
        "test_sdl2_core",
        "test_sdl2_native_audio",
        "test_sdl2_native_video",
        "test_sdl2_native_video_invalid",
    )

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["CMAKE_SKIP_RPATH"] = True
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(cli_args=["--parallel", "1"])
        if str(self.settings.os) == "OHOS":
            for name in self._binary_names:
                self._validate_target_elf(Path(self.cpp.build.bindir, name))

    def test(self):
        binaries = {
            name: Path(self.cpp.build.bindir, name)
            for name in self._binary_names
        }
        for name, path in binaries.items():
            if not path.is_file():
                raise ConanException(f"consumer binary is missing: {name}: {path}")
        if cross_building(self):
            self.output.info(
                "SDL2 consumers: 0/4 NOT_RUN (target execution required)"
            )
            return
        if str(self.settings.os) == "OHOS":
            signing_tools, missing_tools = self._resolve_signing_tools()
            if missing_tools:
                self.output.info(
                    "SDL2 consumers: 0/4 NOT_RUN "
                    f"(OHOS signing tools missing: {', '.join(missing_tools)})"
                )
                return
            for path in binaries.values():
                self._sign_elf(path, signing_tools)
        self.run(self._quoted_binary("test_sdl2_core"), env="conanrun")
        if str(self.settings.os) == "OHOS":
            self.run(
                self._quoted_binary("test_sdl2_native_video_invalid"),
                env="conanrun",
            )
            self.run(
                self._quoted_binary("test_sdl2_native_audio"), env="conanrun"
            )
            self.output.info(
                "SDL2 native video: NOT_RUN in Conan shell; ArkUI surface tuple required"
            )

    def _quoted_binary(self, name):
        path = Path(self.cpp.build.bindir, name)
        if not path.is_file():
            raise ConanException(f"consumer binary is missing: {path}")
        return f'"{path.resolve()}"'

    def _validate_target_elf(self, executable):
        if not executable.is_file():
            raise ConanException(f"consumer binary is missing: {executable}")
        readelf = self._resolve_tool("readelf")
        header = subprocess.run(
            [readelf, "-hW", str(executable)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        if not re.search(r"^\s*Machine:\s+AArch64\s*$", header, re.MULTILINE):
            raise ConanException(f"consumer is not an AArch64 ELF: {executable}")
        dynamic = subprocess.run(
            [readelf, "-dW", str(executable)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        needed = re.findall(r"\(NEEDED\).*?\[([^]]+)\]", dynamic)
        if any("/" in item or "\\" in item for item in needed):
            raise ConanException(
                f"consumer has a path-bearing dependency: {executable}: {needed!r}"
            )
        if re.search(r"\((?:RPATH|RUNPATH)\)", dynamic):
            raise ConanException(
                f"consumer has a packaged RPATH/RUNPATH: {executable}"
            )

    def _resolve_signing_tools(self):
        tools = {}
        missing = []
        for name, llvm in (
            ("objcopy", True),
            ("readelf", True),
            ("binary-sign-tool", False),
        ):
            try:
                tools[name] = self._resolve_tool(name, llvm=llvm)
            except ConanInvalidConfiguration:
                missing.append(name)
        return tools, missing

    def _sign_elf(self, executable, tools):
        if not executable.is_file():
            raise ConanInvalidConfiguration(
                f"required OHOS consumer ELF is missing: {executable}"
            )
        objcopy = tools["objcopy"]
        readelf = tools["readelf"]
        signer = tools["binary-sign-tool"]
        temporary = executable.with_name(f"{executable.name}.signing-{os.getpid()}")
        original_mode = stat.S_IMODE(executable.stat().st_mode)
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
            os.chmod(temporary, original_mode | 0o755)
            self._validate_signed_elf(readelf, temporary)
            os.replace(temporary, executable)
            os.chmod(executable, original_mode | 0o755)
            self._validate_signed_elf(readelf, executable)
        finally:
            if temporary.exists():
                temporary.unlink()

    @staticmethod
    def _validate_signed_elf(readelf, executable):
        sections = subprocess.run(
            [readelf, "-SW", str(executable)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        matches = re.findall(
            r"^\s*\[\s*\d+\]\s+\.codesign\s+\S+\s+"
            r"[0-9A-Fa-f]+\s+[0-9A-Fa-f]+\s+([0-9A-Fa-f]+)\s+",
            sections,
            flags=re.MULTILINE,
        )
        if len(matches) != 1 or int(matches[0], 16) <= 0:
            raise ConanException(
                f"ELF requires one non-empty .codesign section: {executable}"
            )
        if os.name != "nt" and not (
            stat.S_IMODE(Path(executable).stat().st_mode) & stat.S_IXUSR
        ):
            raise ConanException(f"signed ELF lacks owner execute permission: {executable}")

    def _resolve_tool(self, tool, llvm=True):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = executables.get("c") or shutil.which("cc")
        compiler_path = shutil.which(compiler) if compiler else None
        compiler_path = compiler_path or compiler
        compiler_dir = os.path.dirname(compiler_path) if compiler_path else ""
        compiler_name = os.path.basename(compiler_path) if compiler_path else ""
        suffix = (
            compiler_name[len("clang") :]
            if compiler_name.startswith("clang")
            else ""
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
        raise ConanInvalidConfiguration(f"required tool was not found: {tool}")
