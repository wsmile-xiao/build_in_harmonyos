#!/usr/bin/env python3
"""Conan recipe for the ASTAP 2026.07.16 command-line astrometric solver."""

import hashlib
import http.client
import os
import shutil
import subprocess
import tarfile
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class AstapConan(ConanFile):
    name = "astap"
    version = "2024.11.13"
    description = "ASTAP command-line astrometric plate solver"
    license = "MPL-2.0"
    homepage = "https://www.hnsky.org/astap.htm"
    url = "https://github.com/CanardConfit/ASTAP"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    _fpc_version = "3.2.2"
    _fpc_components = (
        "base.aarch64-linux.tar.gz",
        "units-rtl-objpas.aarch64-linux.tar.gz",
        "units-rtl-extra.aarch64-linux.tar.gz",
        "units-fcl-base.aarch64-linux.tar.gz",
        "units-fcl-image.aarch64-linux.tar.gz",
        "units-paszlib.aarch64-linux.tar.gz",
        "units-hash.aarch64-linux.tar.gz",
        "units-pasjpeg.aarch64-linux.tar.gz",
        "utils-fpcres.aarch64-linux.tar.gz",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os != "OHOS" or self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                "astap 2024.11.13 currently supports only OHOS armv8"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        astap = self.conan_data["sources"]["astap"]
        get(self, **astap, strip_root=True)
        fpc_dir = Path(self.source_folder) / "fpc-dist"
        fpc = self.conan_data["sources"]["fpc"]
        fpc_url = str(fpc["url"])
        if fpc_url.startswith("file://"):
            fpc_archive = Path(fpc_url.removeprefix("file://"))
            actual_sha256 = hashlib.sha256(fpc_archive.read_bytes()).hexdigest()
            if actual_sha256 != fpc["sha256"]:
                raise ConanInvalidConfiguration(
                    f"FPC archive checksum mismatch: {actual_sha256}"
                )
            fpc_dir.mkdir(parents=True, exist_ok=True)
            self._extract(fpc_archive, fpc_dir)
        else:
            fpc_dir.mkdir(parents=True, exist_ok=True)
            fpc_archive = fpc_dir / fpc["filename"]
            self._download_parallel(
                fpc_url,
                fpc_archive,
                int(fpc["size"]),
                fpc["sha256"],
            )
            self._extract(fpc_archive, fpc_dir)
        apply_conandata_patches(self)

    @staticmethod
    def _download_part(url, part, start, end):
        request = urllib.request.Request(
            url,
            headers={
                "Range": f"bytes={start}-{end}",
                "User-Agent": "Conan/2 astap-fpc-fetcher",
            },
        )
        expected_range = f"bytes {start}-{end}/"
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=120) as response:
                    content_range = response.headers.get("Content-Range", "")
                    if response.status != 206 or not content_range.startswith(expected_range):
                        raise OSError(
                            f"server rejected byte range {start}-{end}: "
                            f"HTTP {response.status}, Content-Range={content_range!r}"
                        )
                    with part.open("wb") as output:
                        shutil.copyfileobj(response, output, length=1024 * 1024)
                expected_size = end - start + 1
                if part.stat().st_size != expected_size:
                    raise OSError(
                        f"short byte range {start}-{end}: {part.stat().st_size} bytes"
                    )
                return
            except (OSError, TimeoutError, http.client.IncompleteRead) as error:
                part.unlink(missing_ok=True)
                if attempt == 2:
                    raise ConanInvalidConfiguration(
                        f"failed to download FPC byte range {start}-{end}: {error}"
                    ) from error
                time.sleep(2 ** attempt)

    @classmethod
    def _download_parallel(cls, url, destination, size, expected_sha256):
        part_size = 8 * 1024 * 1024
        ranges = [
            (start, min(start + part_size - 1, size - 1))
            for start in range(0, size, part_size)
        ]
        parts = [destination.with_suffix(f"{destination.suffix}.part{index}")
                 for index in range(len(ranges))]
        try:
            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = [
                    executor.submit(cls._download_part, url, part, start, end)
                    for part, (start, end) in zip(parts, ranges)
                ]
                for future in futures:
                    future.result()
            digest = hashlib.sha256()
            with destination.open("wb") as output:
                for part in parts:
                    with part.open("rb") as source:
                        while chunk := source.read(1024 * 1024):
                            output.write(chunk)
                            digest.update(chunk)
            if destination.stat().st_size != size:
                raise ConanInvalidConfiguration(
                    f"FPC archive size mismatch: {destination.stat().st_size}"
                )
            if digest.hexdigest() != expected_sha256:
                raise ConanInvalidConfiguration(
                    f"FPC archive checksum mismatch: {digest.hexdigest()}"
                )
        finally:
            for part in parts:
                part.unlink(missing_ok=True)

    @staticmethod
    def _extract(archive, destination):
        with tarfile.open(archive, "r:*") as source:
            source.extractall(destination, filter="data")

    @staticmethod
    def _sign(binary):
        hnp_bin = Path("/data/service/hnp/bin")
        objcopy = hnp_bin / "llvm-objcopy"
        sign_tool = hnp_bin / "binary-sign-tool"
        if not sign_tool.exists():
            raise ConanInvalidConfiguration("HarmonyOS binary-sign-tool is required")
        subprocess.run(
            [str(objcopy), "--remove-section", ".codesign", str(binary)],
            check=False,
        )
        signed = binary.with_suffix(binary.suffix + ".signed")
        subprocess.run(
            [str(sign_tool), "sign", "-inFile", str(binary),
             "-outFile", str(signed), "-selfSign", "1"],
            check=True,
        )
        shutil.move(signed, binary)
        os.chmod(binary, 0o755)

    def build(self):
        fpc_dist = Path(self.source_folder) / "fpc-dist"
        binary_archive = next(fpc_dist.rglob("binary.aarch64-linux.tar"))
        toolchain = Path(self.build_folder) / "fpc-toolchain"
        toolchain.mkdir(parents=True, exist_ok=True)
        self._extract(binary_archive, toolchain)
        for component in self._fpc_components:
            archive = next(toolchain.rglob(component))
            self._extract(archive, toolchain)

        compiler = toolchain / "lib" / "fpc" / self._fpc_version / "ppca64"
        fpcres = toolchain / "bin" / "fpcres"
        self._sign(compiler)
        self._sign(fpcres)

        unit_root = toolchain / "lib" / "fpc" / self._fpc_version / "units" / "aarch64-linux"
        unit_dirs = (
            "rtl", "rtl-objpas", "rtl-extra", "fcl-base", "fcl-image",
            "paszlib", "hash", "pasjpeg",
        )
        output = Path(self.build_folder) / "astap_cli"
        command = [
            str(compiler), "-B", "-MObjFPC", "-Scghi", "-O2",
            f"-FE{self.build_folder}", f"-o{output.name}",
        ]
        command.extend(f"-Fu{unit_root / unit}" for unit in unit_dirs)
        cli_source = Path(self.source_folder) / "command-line_version"
        command.append("astap_command_line.lpr")
        env = os.environ.copy()
        env["PATH"] = f"{toolchain / 'bin'}{os.pathsep}{env.get('PATH', '')}"
        subprocess.run(command, cwd=cli_source, env=env, check=True)
        self._sign(output)

    def package(self):
        copy(self, "astap_cli", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
