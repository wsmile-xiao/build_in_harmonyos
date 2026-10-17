#!/usr/bin/env python3
"""Installed-package consumer for libopusenc 0.3."""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class LibopusencTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("opus/1.5.2.1")

    def layout(self):
        cmake_layout(self)

    @staticmethod
    def _dependency_library(dependency):
        candidates = []
        for libdir in dependency.cpp_info.libdirs:
            for library in dependency.cpp_info.libs:
                for filename in (f"lib{library}.so", f"lib{library}.a"):
                    path = os.path.join(dependency.package_folder, libdir, filename)
                    if os.path.isfile(path):
                        candidates.append(path)
        if len(candidates) != 1:
            raise ConanException(
                f"Expected one library for {dependency.ref}, got {candidates}"
            )
        return candidates[0].replace("\\", "/")

    def generate(self):
        dependencies = CMakeDeps(self)
        dependencies.set_property("opus", "cmake_file_name", "Opus")
        dependencies.set_property("opus", "cmake_target_name", "Opus::opus")
        dependencies.generate()
        toolchain = CMakeToolchain(self)
        toolchain.variables["LIBOPUSENC_TEST_OPUS_INCLUDE"] = os.path.join(
            self.dependencies["opus"].package_folder,
            "include",
        ).replace("\\", "/")
        toolchain.variables["LIBOPUSENC_TEST_OPUS_LIBRARY"] = self._dependency_library(
            self.dependencies["opus"]
        )
        toolchain.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    @staticmethod
    def _ohos_tool(name):
        path = shutil.which(name) or os.path.join("/data/service/hnp/bin", name)
        if not os.path.isfile(path):
            raise ConanException(f"Required OHOS tool is missing: {name}")
        return path

    def _sign_ohos_elf(self, path):
        readelf = self._readelf()
        objcopy = self._ohos_tool("llvm-objcopy")
        signer = self._ohos_tool("binary-sign-tool")
        sections = subprocess.run(
            [readelf, "-SW", path],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        codesign_count = sections.count(".codesign")
        if codesign_count == 1:
            self.output.info(f"Preserving existing .codesign section: {path}")
            return
        if codesign_count != 0:
            raise ConanException(f"Consumer has invalid .codesign count: {codesign_count}")
        clean = path + ".codesign-clean"
        signed = path + ".libopusenc-signed"
        for generated in (clean, signed):
            if os.path.exists(generated):
                os.remove(generated)
        try:
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", path, clean],
                check=True,
                timeout=30,
            )
            subprocess.run(
                [
                    signer,
                    "sign",
                    "-inFile",
                    clean,
                    "-outFile",
                    signed,
                    "-selfSign",
                    "1",
                ],
                check=True,
                timeout=60,
            )
            sections = subprocess.run(
                [readelf, "-SW", signed],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            ).stdout
            if sections.count(".codesign") != 1:
                raise ConanException("Signed consumer has invalid .codesign count")
            os.chmod(signed, (os.stat(path).st_mode & 0o777) | 0o055)
            os.replace(signed, path)
        finally:
            for generated in (clean, signed):
                if os.path.exists(generated):
                    os.remove(generated)

    def _readelf(self):
        # GNU readelf is on PATH on the OHOS device; llvm-readelf is not.
        return self._ohos_tool("readelf")

    @staticmethod
    def _ar_tool():
        # OHOS toolchains ship llvm-ar; a plain binutils ar may be absent.
        ar_tool = shutil.which("llvm-ar") or shutil.which("ar")
        if not ar_tool:
            raise ConanException("Neither llvm-ar nor ar was found in PATH")
        return ar_tool

    def _check_ohos_elf(self, path, soname=None):
        """HarmonyOS-specific ELF verification: class/machine, SONAME, NEEDED, RPATH."""
        readelf = self._readelf()
        dynamic = subprocess.run(
            [readelf, "-dW", path],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        header = subprocess.run(
            [readelf, "-hW", path],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if "ELF64" not in header or "AArch64" not in header:
            raise ConanException(f"Consumer is not ELF64 AArch64: {path}")
        if soname is not None and f"Library soname: [{soname}]" not in dynamic:
            raise ConanException(f"Missing SONAME {soname}: {path}")
        needed = [l for l in dynamic.splitlines() if "NEEDED" in l]
        if not needed:
            raise ConanException(f"Missing NEEDED entries: {path}")
        for line in dynamic.splitlines():
            if "RPATH" in line or "RUNPATH" in line:
                raise ConanException(f"Unexpected RPATH/RUNPATH: {line}")
        self.output.info(f"ELF64 AArch64 verified, no RPATH/RUNPATH: {path}")
        for line in needed:
            self.output.info(f"NEEDED: {line.strip()}")

    def _check_static_library(self, archive):
        """Verify a static library exists and its members are AArch64 ELF."""
        readelf = self._readelf()
        ar_tool = self._ar_tool()
        if not os.path.isfile(archive):
            raise ConanException(f"Static library is missing: {archive}")
        archived = subprocess.run(
            [ar_tool, "t", archive],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        members = [m for m in archived.split() if m.endswith(".o")]
        if not members:
            raise ConanException(f"Static archive has no object members: {archive}")
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(
                [ar_tool, "x", archive, members[0]],
                check=True,
                timeout=30,
                cwd=tmp,
            )
            extracted_path = os.path.join(tmp, members[0])
            header = subprocess.run(
                [readelf, "-hW", extracted_path],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            ).stdout
            if "ELF" not in header or "AArch64" not in header:
                raise ConanException(f"Archive member is not ELF AArch64: {members[0]}")
        self.output.info(f"Static archive members verified AArch64 ELF: {archive}")

    def test(self):
        if not can_run(self):
            self.output.info("NOT_RUN: target consumer execution is unavailable while cross-building")
            return
        executable = os.path.join(self.cpp.build.bindir, "libopusenc_consumer")
        dependency = self.dependencies["libopusenc"]
        library = dependency.cpp_info.libs[0]
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_elf(executable)
            # HarmonyOS-specific checks: ELF64 AArch64, NEEDED, no RPATH/RUNPATH;
            # static builds additionally verify the archive members are AArch64 ELF.
            libdir = dependency.cpp_info.libdirs[0]
            shared_path = os.path.join(dependency.package_folder, libdir, f"lib{library}.so")
            static_path = os.path.join(dependency.package_folder, libdir, f"lib{library}.a")
            if os.path.isfile(shared_path):
                self._check_ohos_elf(shared_path, soname=f"lib{library}.so")
                self._check_ohos_elf(executable)
            elif os.path.isfile(static_path):
                self._check_static_library(static_path)
            else:
                raise ConanException(f"No libopusenc library found in {dependency.package_folder}")
        self.run(f'"{executable}"', env="conanrun", cwd=self.cpp.build.bindir)
