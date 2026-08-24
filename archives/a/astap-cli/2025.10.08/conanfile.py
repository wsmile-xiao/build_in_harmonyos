#!/usr/bin/env python3
"""Conan recipe for the ASTAP CLI 2025.10.08 command-line solver."""

import hashlib
import os
import shutil
import subprocess
import tarfile
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class AstapCliConan(ConanFile):
    name = "astap-cli"
    version = "2025.10.08"
    description = "ASTAP command-line astrometric plate solver"
    license = "MPL-2.0"
    homepage = "https://www.hnsky.org/astap.htm"
    url = "https://salsa.debian.org/debian-astro-team/astap-cli"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    _fpc_components = (
        "base.aarch64-linux.tar.gz", "units-rtl-objpas.aarch64-linux.tar.gz",
        "units-rtl-extra.aarch64-linux.tar.gz", "units-fcl-base.aarch64-linux.tar.gz",
        "units-fcl-image.aarch64-linux.tar.gz", "units-paszlib.aarch64-linux.tar.gz",
        "units-hash.aarch64-linux.tar.gz", "units-pasjpeg.aarch64-linux.tar.gz",
        "utils-fpcres.aarch64-linux.tar.gz",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os != "OHOS" or self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("astap-cli supports only OHOS armv8")

    def layout(self):
        basic_layout(self)

    def source(self):
        astap = self.conan_data["sources"]["astap_cli"]
        astap_url = str(astap["url"])
        if astap_url.startswith("file://"):
            archive = self._cached_archive(astap_url, astap["sha256"])
            self._extract(archive, self.source_folder, strip_root=True)
        else:
            get(self, **astap, strip_root=True)

        fpc = self.conan_data["sources"]["fpc"]
        fpc_dir = Path(self.source_folder) / "fpc-dist"
        fpc_url = str(fpc["url"])
        if fpc_url.startswith("file://"):
            archive = self._cached_archive(fpc_url, fpc["sha256"])
            fpc_dir.mkdir(parents=True, exist_ok=True)
            self._extract(archive, fpc_dir)
        else:
            get(self, **fpc, destination=str(fpc_dir))
        apply_conandata_patches(self)

    @staticmethod
    def _cached_archive(url, expected_sha256):
        requested = Path(url.removeprefix("file://"))
        candidates = [requested]
        if requested.parent.exists():
            candidates.extend(requested.parent.rglob("*"))
        for candidate in candidates:
            if candidate.is_file():
                try:
                    if hashlib.sha256(candidate.read_bytes()).hexdigest() == expected_sha256:
                        return candidate
                except OSError:
                    continue
        raise ConanInvalidConfiguration(
            f"cached source with SHA-256 {expected_sha256} was not found"
        )

    @staticmethod
    def _extract(archive, destination, strip_root=False):
        with tarfile.open(archive, "r:*") as source:
            if not strip_root:
                source.extractall(destination, filter="data")
                return
            members = source.getmembers()
            roots = {member.name.split("/", 1)[0] for member in members if member.name}
            prefix = next(iter(roots)) + "/" if len(roots) == 1 else ""
            for member in members:
                if not member.name.startswith(prefix):
                    continue
                member.name = member.name[len(prefix):]
                if member.name:
                    source.extract(member, destination, filter="data")

    @staticmethod
    def _sign(binary):
        hnp = Path("/data/service/hnp/bin")
        sign_tool = hnp / "binary-sign-tool"
        objcopy = hnp / "llvm-objcopy"
        if not sign_tool.exists():
            raise ConanInvalidConfiguration("binary-sign-tool is required")
        subprocess.run([str(objcopy), "--remove-section", ".codesign", str(binary)], check=False)
        signed = binary.with_suffix(binary.suffix + ".signed")
        subprocess.run([str(sign_tool), "sign", "-inFile", str(binary), "-outFile", str(signed), "-selfSign", "1"], check=True)
        shutil.move(signed, binary)
        os.chmod(binary, 0o755)

    def build(self):
        fpc_dist = Path(self.source_folder) / "fpc-dist"
        toolchain = Path(self.build_folder) / "fpc-toolchain"
        toolchain.mkdir(parents=True, exist_ok=True)
        self._extract(next(fpc_dist.rglob("binary.aarch64-linux.tar")), toolchain)
        for component in self._fpc_components:
            self._extract(next(toolchain.rglob(component)), toolchain)
        compiler = toolchain / "lib/fpc/3.2.2/ppca64"
        fpcres = toolchain / "bin/fpcres"
        self._sign(compiler)
        self._sign(fpcres)
        units = toolchain / "lib/fpc/3.2.2/units/aarch64-linux"
        unit_dirs = ("rtl", "rtl-objpas", "rtl-extra", "fcl-base", "fcl-image", "paszlib", "hash", "pasjpeg")
        output = Path(self.build_folder) / "astap_cli"
        command = [str(compiler), "-B", "-MObjFPC", "-Scghi", "-O2", f"-FE{self.build_folder}", f"-o{output.name}"]
        command.extend(f"-Fu{units / item}" for item in unit_dirs)
        command.append("astap_command_line.lpr")
        env = os.environ.copy()
        env["PATH"] = f"{toolchain / 'bin'}{os.pathsep}{env.get('PATH', '')}"
        subprocess.run(command, cwd=self.source_folder, env=env, check=True)
        self._sign(output)

    def package(self):
        copy(self, "astap_cli", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "copyright.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
