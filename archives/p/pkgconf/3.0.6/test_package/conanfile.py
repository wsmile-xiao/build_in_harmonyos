#!/usr/bin/env python3
"""Consumer and command tests for pkgconf 3.0.6."""

import hashlib
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class PkgconfTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(cli_args=["-j1"])

    def _run(self, argv, env=None):
        result = subprocess.run(
            argv,
            cwd=self.source_folder,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode != 0:
            command = " ".join(argv)
            raise ConanException(
                f"command failed ({result.returncode}): {command}\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )
        return result.stdout

    def _find_ohos_runtime_tool(self, name):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compiler_executables.get("c") or compiler_executables.get("cpp", "")
        compiler_path = shutil.which(compiler) or compiler
        compiler_dir = os.path.dirname(compiler_path)
        candidates = [
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        ]
        for candidate in candidates:
            resolved = shutil.which(candidate) or candidate
            if resolved and os.path.isfile(resolved) and not os.path.islink(resolved):
                return os.path.abspath(resolved)
        return ""

    @staticmethod
    def _file_sha256(path):
        digest = hashlib.sha256()
        with open(path, "rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _run_signing_tool(argv, label):
        completed = subprocess.run(
            argv,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if completed.returncode != 0:
            raise ConanException(
                f"{label} failed ({completed.returncode}): "
                f"{completed.stderr.strip()}"
            )
        return completed.stdout

    def _elf_sections(self, readelf, path):
        output = self._run_signing_tool([readelf, "-S", path], "llvm-readelf")
        if ".note.ohos.ident" not in output:
            raise ConanException(f"ELF platform identity section missing: {path}")
        return output

    def _sign_elf_atomically(self, path, objcopy, readelf, signer):
        if not os.path.isfile(path) or os.path.islink(path):
            raise ConanException(f"unsafe ELF signing input: {path}")
        with open(path, "rb") as stream:
            if stream.read(4) != b"\x7fELF":
                raise ConanException(f"signing input is not ELF: {path}")

        unsigned_sha256 = self._file_sha256(path)
        temporary = f"{path}.unsigned-for-signing"
        signed = f"{path}.signed"
        if os.path.lexists(temporary) or os.path.lexists(signed):
            raise ConanException(f"stale signing transaction beside: {path}")
        try:
            shutil.copy2(path, temporary)
            sections = self._elf_sections(readelf, temporary)
            if ".codesign" in sections:
                self._run_signing_tool(
                    [objcopy, "--remove-section", ".codesign", temporary],
                    "llvm-objcopy",
                )
                self._elf_sections(readelf, temporary)
            self._run_signing_tool(
                [
                    signer,
                    "sign",
                    "-inFile",
                    temporary,
                    "-outFile",
                    signed,
                    "-selfSign",
                    "1",
                ],
                "binary-sign-tool",
            )
            if not os.path.isfile(signed) or os.path.islink(signed):
                raise ConanException(f"signer did not create a regular output: {path}")
            signed_sections = self._elf_sections(readelf, signed)
            if ".codesign" not in signed_sections:
                raise ConanException(f"signed ELF has no .codesign section: {path}")
            os.chmod(signed, 0o755)
            signed_sha256 = self._file_sha256(signed)
            if signed_sha256 == unsigned_sha256:
                raise ConanException(f"ELF signing did not change the file: {path}")
            os.replace(signed, path)
        finally:
            for residue in (temporary, signed):
                if os.path.lexists(residue):
                    os.remove(residue)

    def _prepare_ohos_execution(self, test_binary, commands):
        tools = {
            "objcopy": self._find_ohos_runtime_tool("llvm-objcopy"),
            "readelf": self._find_ohos_runtime_tool("llvm-readelf"),
            "signer": self._find_ohos_runtime_tool("binary-sign-tool"),
        }
        missing = [name for name, path in tools.items() if not path]
        if missing:
            self.output.info(
                "TARGET_RUNTIME_TESTS=NOT_RUN: OHOS signing tools unavailable: "
                + ", ".join(missing)
            )
            return None

        self._sign_elf_atomically(
            test_binary, tools["objcopy"], tools["readelf"], tools["signer"]
        )
        runtime_bin = os.path.join(self.build_folder, "signed-package-bin")
        if os.path.lexists(runtime_bin):
            raise ConanException(f"stale signed command directory: {runtime_bin}")
        os.makedirs(runtime_bin)
        signed_commands = {}
        for name, source in commands.items():
            destination = os.path.join(runtime_bin, os.path.basename(source))
            shutil.copy2(source, destination)
            self._sign_elf_atomically(
                destination,
                tools["objcopy"],
                tools["readelf"],
                tools["signer"],
            )
            signed_commands[name] = destination
        return signed_commands

    def test(self):
        test_binary = os.path.join(
            self.cpp.build.bindirs[0],
            "test_pkgconf.exe" if self.settings.os == "Windows" else "test_pkgconf",
        )
        dependency = self.dependencies[self.tested_reference_str]
        suffix = ".exe" if self.settings.os == "Windows" else ""
        bindir = os.path.join(dependency.package_folder, "bin")
        commands = {
            name: os.path.join(bindir, name + suffix)
            for name in ("pkgconf", "bomtool", "spdxtool", "pccritic")
        }
        if not os.path.isfile(test_binary):
            raise ConanException(f"missing consumer binary: {test_binary}")
        missing = [name for name, path in commands.items() if not os.path.isfile(path)]
        if missing:
            raise ConanException("missing command binaries: " + ", ".join(missing))

        if not can_run(self):
            self.output.info(
                "TARGET_RUNTIME_TESTS=NOT_RUN: build/host settings are not runnable"
            )
            self.output.info("CONSUMER_COMPILE_LINK_TESTS=1/1")
            self.output.info("CLI_RUNTIME_TESTS=NOT_RUN")
            return

        if self.settings.os == "OHOS":
            prepared_commands = self._prepare_ohos_execution(test_binary, commands)
            if prepared_commands is None:
                self.output.info("CONSUMER_COMPILE_LINK_TESTS=1/1")
                self.output.info("CLI_RUNTIME_TESTS=NOT_RUN")
                return
            commands = prepared_commands

        self.run(test_binary, env="conanrun")

        for name, path in commands.items():
            if "3.0.6" not in self._run([path, "--version"]):
                raise ConanException(f"{name} --version did not report 3.0.6")

        fixture = os.path.join(
            self.source_folder, "fixtures", "pkgconf-fixture.pc"
        )
        env = os.environ.copy()
        env["PKG_CONFIG_PATH"] = os.path.dirname(fixture)
        env["PKG_CONFIG_LIBDIR"] = ""

        version = self._run(
            [commands["pkgconf"], "--modversion", "pkgconf-fixture"], env
        ).strip()
        if version != "1.2.3":
            raise ConanException(f"unexpected pkgconf module version: {version}")

        cflags = self._run(
            [commands["pkgconf"], "--cflags", "pkgconf-fixture"], env
        ).split()
        if cflags != ["-I/test/include"]:
            raise ConanException(f"unexpected pkgconf cflags: {cflags}")

        libs = self._run(
            [commands["pkgconf"], "--libs", "pkgconf-fixture"], env
        ).split()
        if libs != ["-L/test/lib", "-lpkgconf_fixture"]:
            raise ConanException(f"unexpected pkgconf libs: {libs}")

        bom = self._run(
            [
                commands["bomtool"],
                "--creation-time=2026-08-10T00:00:00Z",
                "pkgconf-fixture",
            ],
            env,
        )
        for expected in ("SPDXVersion: SPDX-2.2", "PackageName: pkgconf-fixture@1.2.3"):
            if expected not in bom:
                raise ConanException(f"bomtool output omitted: {expected}")

        spdx = json.loads(
            self._run(
                [
                    commands["spdxtool"],
                    "--creation-time=2026-08-10T00:00:00Z",
                    "pkgconf-fixture",
                ],
                env,
            )
        )
        if spdx.get("@context") != "https://spdx.org/rdf/3.0.1/spdx-context.jsonld":
            raise ConanException("spdxtool emitted an unexpected JSON-LD context")
        packages = [
            item
            for item in spdx.get("@graph", [])
            if item.get("type") == "software_Package"
        ]
        if len(packages) != 1:
            raise ConanException("spdxtool did not emit exactly one software package")
        if packages[0].get("name") != "pkgconf-fixture":
            raise ConanException("spdxtool emitted an unexpected package name")
        if packages[0].get("software_packageVersion") != "1.2.3":
            raise ConanException("spdxtool emitted an unexpected package version")

        critic = self._run(
            [commands["pccritic"], "--quiet", fixture], env
        )
        if "100/100 (A)" not in critic:
            raise ConanException(f"pccritic did not award an A grade: {critic}")

        self.output.info("CLI_FUNCTIONAL_TESTS=4")
        self.output.info("CLI_ASSERTIONS=14")
