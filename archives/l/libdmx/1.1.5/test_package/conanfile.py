#!/usr/bin/env python3
"""Installed-package API tests for libdmx 1.1.5."""

import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


TEST_EXECUTABLES = (
    "libdmx_api_surface",
    "libdmx_version_contract",
    "libdmx_ohos_abi_contract",
)

# Shared libraries the installed libdmx.so.1 must declare as NEEDED.
EXPECTED_NEEDED = ("libX11.so.6", "libXext.so.6", "libc.so")
# The expected SONAME of the shared library.
EXPECTED_SONAME = "libdmx.so.1"


class LibdmxTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "*.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            raise ConanException("libdmx target consumers are not runnable")
        self._verify_installed_library()
        runtime_dir = None
        try:
            if str(self.settings.os) == "OHOS":
                runtime_dir = tempfile_dir()
                for name in TEST_EXECUTABLES:
                    executable = os.path.join(self.cpp.build.bindir, name)
                    staged = os.path.join(runtime_dir, name)
                    shutil.copy2(executable, staged)
                    self._sign_ohos_elf(staged)
                    self.run(f'"{staged}"', env="conanrun")
            else:
                for name in TEST_EXECUTABLES:
                    executable = os.path.join(self.cpp.build.bindir, name)
                    self.run(f'"{executable}"', env="conanrun")
        finally:
            if runtime_dir is not None:
                shutil.rmtree(runtime_dir, ignore_errors=True)

    def _verify_installed_library(self):
        """OHOS ELF gate for the installed libdmx library.

        Shared build: ELF64 AArch64, SONAME libdmx.so.1, NEEDED closure
        (libX11.so.6, libXext.so.6, libc.so), and no host paths in
        RPATH/RUNPATH.  Static build: libdmx.a exists, no libdmx.so*
        is installed, and every archive member is an ELF64 AArch64
        relocatable object.
        """
        tested_package = self._tested_package()
        lib_dir = os.path.join(tested_package.package_folder, "lib")
        shared_library = os.path.join(lib_dir, "libdmx.so.1")
        if not os.path.isfile(shared_library):
            shared_library = os.path.join(lib_dir, "libdmx.so")
        static_library = os.path.join(lib_dir, "libdmx.a")
        if os.path.isfile(shared_library):
            self._verify_shared_library(shared_library)
        elif os.path.isfile(static_library):
            self._verify_static_library(lib_dir, static_library)
        else:
            raise ConanException("installed libdmx library is missing")

    def _tested_package(self):
        host_dependencies = list(self.dependencies.host.values())
        tested_package = next(
            (
                dependency
                for dependency in host_dependencies
                if dependency.ref.name == "libdmx"
            ),
            None,
        )
        if tested_package is None:
            raise ConanException("tested libdmx package is not a host dependency")
        return tested_package

    def _readelf(self):
        readelf = (
            shutil.which("llvm-readelf")
            or shutil.which("readelf")
            or "/data/service/hnp/bin/llvm-readelf"
        )
        if not os.path.isfile(readelf):
            raise ConanException("no readelf available for the ELF gate")
        return readelf

    def _run_tool(self, args):
        return subprocess.run(
            args,
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        ).stdout

    def _verify_shared_library(self, library):
        readelf = self._readelf()
        header = self._run_tool([readelf, "-h", library])
        if "Class:                             ELF64" not in header:
            raise ConanException(f"libdmx is not ELF64: {library}")
        if "Machine:" not in header or "AArch64" not in header:
            raise ConanException(f"libdmx is not AArch64: {library}")
        dynamic = self._run_tool([readelf, "-d", library])
        needed = re.findall(r"\[(.*?)\]", "".join(
            line.split(":", 1)[1] for line in dynamic.splitlines()
            if "NEEDED" in line
        ))
        for expected in EXPECTED_NEEDED:
            if expected not in needed:
                raise ConanException(
                    f"libdmx does not declare {expected} as NEEDED: {needed}"
                )
        soname = re.findall(r"Library soname: \[(.*?)\]", dynamic)
        if soname != [EXPECTED_SONAME]:
            raise ConanException(
                f"libdmx SONAME mismatch: expected {EXPECTED_SONAME},"
                f" got {soname}"
            )
        for line in dynamic.splitlines():
            if "RPATH" not in line and "RUNPATH" not in line:
                continue
            entry = re.findall(r"\[(.*?)\]", line)
            for path in entry:
                # Host build-tree or cache paths must never leak into the
                # package.  Only relocatable entries ($ORIGIN-relative) or
                # system library dirs are acceptable.
                if path.startswith("$ORIGIN") or path in ("/system/lib64",):
                    continue
                raise ConanException(
                    f"libdmx embeds a non-relocatable RPATH entry: {line.strip()}"
                )
        self.output.info(
            f"libdmx ELF gate passed: ELF64 AArch64, SONAME={EXPECTED_SONAME},"
            f" NEEDED={needed}"
        )

    def _verify_static_library(self, lib_dir, static_library):
        strays = sorted(
            entry
            for entry in os.listdir(lib_dir)
            if entry.startswith("libdmx.so")
        )
        if strays:
            raise ConanException(
                f"static package must not ship libdmx.so* artifacts: {strays}"
            )
        readelf = self._readelf()
        header = self._run_tool([readelf, "-h", static_library])
        # readelf walks every archive member and prints one ELF header per
        # member; libdmx's archive contains the single dmx.o member.
        members = header.count("ELF Header:")
        if members == 0:
            raise ConanException(f"libdmx.a has no ELF members: {static_library}")
        if "Class:                             ELF64" not in header:
            raise ConanException(f"libdmx.a members are not ELF64: {static_library}")
        if "Machine:" not in header or "AArch64" not in header:
            raise ConanException(f"libdmx.a members are not AArch64: {static_library}")
        self.output.info(
            f"libdmx ELF gate passed: static archive, {members} member(s),"
            " all ELF64 AArch64, no libdmx.so* shipped"
        )

    def _sign_ohos_elf(self, path):
        signer = shutil.which("binary-sign-tool") or (
            "/data/service/hnp/bin/binary-sign-tool"
        )
        readelf = (
            shutil.which("llvm-readelf")
            or shutil.which("readelf")
            or "/data/service/hnp/bin/llvm-readelf"
        )
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("required OHOS signing tools are missing")
        temporary = f"{path}.signed"
        subprocess.run(
            [
                signer,
                "sign",
                "-inFile",
                path,
                "-outFile",
                temporary,
                "-selfSign",
                "1",
            ],
            check=True,
            timeout=60,
        )
        sections = subprocess.run(
            [readelf, "-SW", temporary],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException(f"signed consumer has invalid .codesign: {path}")
        os.chmod(temporary, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(temporary, path)


def tempfile_dir():
    import tempfile

    return tempfile.mkdtemp(
        prefix="libdmx-test-", dir="/data/storage/el2/base/cache"
    )
