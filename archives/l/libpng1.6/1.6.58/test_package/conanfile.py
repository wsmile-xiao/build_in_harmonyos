#!/usr/bin/env python3
"""Conan consumer test for libpng1.6 1.6.58."""

import json
import os
import re
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
        libpng_dependency = self.dependencies["libpng1.6"]
        dep = libpng_dependency.cpp_info
        incs = []
        libdirs = []
        libs = []
        ordered_dependencies = [libpng_dependency]
        ordered_dependencies.extend(
            dependency
            for _ref, dependency in self.dependencies.items()
            if dependency.ref.name != "libpng1.6"
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
        if cross_building(self):
            self.output.info("cross-building: compile and link only")
            return
        log_path = os.path.join(self.build_folder, "test_probe.log")
        try:
            self.run(f'"./test_probe" > "{log_path}" 2>&1', env="conanrun")
        except ConanException:
            pass
        out = ""
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                out = f.read()
        except OSError:
            out = ""
        self.output.info("test output:\n" + out)
        discovered = 3
        passed_count = len(re.findall(r"^\[PASS\]", out, re.M))
        marker = {
            "executed": True,
            "passed": discovered > 0 and passed_count == discovered,
            "command": "./test_probe (version + read/write struct + IHDR)",
            "discovered": discovered,
            "passedCount": passed_count,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
        if not marker["passed"]:
            raise ConanException(
                f"test_package failed: {passed_count}/{discovered} checks passed"
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

    def _probe_live_program(self, candidate):
        try:
            subprocess.check_output([candidate, '--version'], stderr=subprocess.STDOUT, text=True, timeout=30)
            return True
        except Exception:
            return False

    def _c_compiler(self):
        # [stale_conf_cc v2] 与主配方同理：版本命令实测探活。
        try:
            executables = self.conf.get('tools.build:compiler_executables', default={}, check_type=dict)
        except Exception:
            executables = {}
        conf_cc = executables.get('c') if isinstance(executables, dict) else None
        candidates = []
        if conf_cc:
            candidates.append(str(conf_cc))
            if os.path.isabs(str(conf_cc)):
                which_base = shutil.which(os.path.basename(str(conf_cc)))
                if which_base:
                    candidates.append(which_base)
        for candidate in ('clang', 'cc', 'gcc'):
            resolved = shutil.which(candidate)
            if resolved:
                candidates.append(resolved)
        seen = set()
        for candidate in candidates:
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            resolved = shutil.which(candidate) or candidate
            if resolved and os.path.isfile(resolved) and self._probe_live_program(resolved):
                return resolved
        raise ConanInvalidConfiguration('No live C compiler found')
