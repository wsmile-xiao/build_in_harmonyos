#!/usr/bin/env python3
"""Conan recipe for the Artistic Style library."""

import hashlib
import os
import shutil
import stat
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, export_conandata_patches, get


class AStyleConan(ConanFile):
    name = "astyle"
    version = "3.6.18"
    description = "C++ source code formatter and beautifier library"
    license = "MIT"
    homepage = "https://gitlab.com/saalen/astyle"
    url = "https://gitlab.com/saalen/astyle"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"astyle is supported only on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            strip_root=True,
            filename="astyle-3.6.18.tar.gz",
        )

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        toolchain.variables["BUILD_STATIC_LIBS"] = not bool(self.options.shared)
        toolchain.variables["BUILD_JAVA_LIBS"] = False
        toolchain.variables["INSTALL_DOC"] = False
        if self.options.get_safe("fPIC") is not None:
            toolchain.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(
                self.options.fPIC
            )
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        if not cross_building(self):
            self._run_upstream_regression()

    def _run_upstream_regression(self):
        """Build the upstream CLI and run its complete shell regression suite."""
        cli_build = os.path.join(self.build_folder, "upstream-cli")
        cli_source = os.path.join(self.source_folder, "AStyle")
        self.run(
            f'cmake -S "{cli_source}" -B "{cli_build}" '
            "-DCMAKE_BUILD_TYPE=Release -DBUILD_STATIC_LIBS=OFF "
            "-DBUILD_SHARED_LIBS=OFF -DBUILD_JAVA_LIBS=OFF -DINSTALL_DOC=OFF"
        )
        self.run(f'cmake --build "{cli_build}" --parallel 1')

        staging_parent = (
            "/data/storage/el2/base/cache"
            if str(self.settings.os) == "OHOS"
            else self.build_folder
        )
        regression_root = tempfile.mkdtemp(
            prefix="astyle-regression-",
            dir=staging_parent,
        )
        try:
            shutil.copytree(
                os.path.join(self.source_folder, "AStyleTest"),
                os.path.join(regression_root, "AStyleTest"),
            )
            regression_bin = os.path.join(
                regression_root,
                "AStyle",
                "build_local",
            )
            os.makedirs(regression_bin, exist_ok=True)
            cli_name = (
                "astyle.exe"
                if str(self.settings.os) == "Windows"
                else "astyle"
            )
            regression_cli = os.path.join(regression_bin, cli_name)
            shutil.copy2(os.path.join(cli_build, cli_name), regression_cli)
            os.chmod(
                regression_cli,
                os.stat(regression_cli).st_mode
                | stat.S_IXUSR
                | stat.S_IXGRP
                | stat.S_IXOTH,
            )
            if str(self.settings.os) == "OHOS":
                signer = self._resolve_ohos_signer(regression_root)
                self._sign_elf_atomically(regression_cli, signer)
            regression_dir = os.path.join(
                regression_root,
                "AStyleTest",
                "regression-sh",
            )
            self.run("bash ./run_tests.sh", cwd=regression_dir)
        finally:
            shutil.rmtree(regression_root, ignore_errors=True)

    def _resolve_ohos_signer(self, regression_root):
        system_signer = self._find_ohos_runtime_tool("binary-sign-tool")
        if system_signer:
            return system_signer

        signer_data = self.conan_data["tools"]["ohos_signer"]
        signer_root = os.path.join(regression_root, "ohos-signer")
        get(
            self,
            url=signer_data["url"],
            sha256=signer_data["sha256"],
            destination=signer_root,
            keep_permissions=True,
        )
        signer = os.path.join(signer_root, "bin", "binary-sign-tool")
        if not os.path.isfile(signer) or os.path.islink(signer):
            raise ConanException(f"official OHOS signer is missing or unsafe: {signer}")
        signer_sha256 = self._file_sha256(signer)
        if signer_sha256 != signer_data["binary_sha256"]:
            raise ConanException(
                "official OHOS signer payload hash mismatch: "
                f"{signer_sha256}"
            )
        os.chmod(signer, 0o755)
        return signer

    def _find_ohos_runtime_tool(self, name):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compiler_executables.get("c") or compiler_executables.get(
            "cpp", ""
        )
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
                f"{completed.stdout.strip()} {completed.stderr.strip()}"
            )
        return completed.stdout + completed.stderr

    def _sign_elf_atomically(self, path, signer):
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
                raise ConanException(
                    f"signer did not create a regular output: {path}"
                )
            display = self._run_signing_tool(
                [signer, "display-sign", "-inFile", signed],
                "binary-sign-tool display-sign",
            )
            if "code signature is self-sign" not in display:
                raise ConanException(
                    f"signed ELF did not verify as self-sign: {path}"
                )

            os.chmod(signed, 0o755)
            signed_sha256 = self._file_sha256(signed)
            if signed_sha256 == unsigned_sha256:
                raise ConanException(f"ELF signing did not change the file: {path}")
            os.replace(signed, path)
            self.output.info(
                f"SIGNED_ELF={os.path.basename(path)} "
                f"UNSIGNED_SHA256={unsigned_sha256} "
                f"SIGNED_SHA256={signed_sha256}"
            )
        finally:
            for residue in (temporary, signed):
                if os.path.lexists(residue):
                    os.remove(residue)

    def package(self):
        CMake(self).install()
        src = os.path.join(self.source_folder, "AStyle", "src")
        include = os.path.join(self.package_folder, "include")
        copy(self, "astyle.h", src=src, dst=include)
        copy(self, "astyle_main.h", src=src, dst=include)
        copy(self, "LICENSE.md", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["astyle"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.defines = ["ASTYLE_LIB"]
        self.cpp_info.set_property("cmake_file_name", "astyle")
        self.cpp_info.set_property("cmake_target_name", "astyle::astyle")
        self.cpp_info.set_property("pkg_config_name", "astyle")
