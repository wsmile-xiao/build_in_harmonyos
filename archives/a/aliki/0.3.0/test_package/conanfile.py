#!/usr/bin/env python3
"""Conan test_package for aliki 0.3.0 — packaged-tool smoke test.

aliki is an X11 GUI tool and aliki-rt a real-time capture program; neither
can run to completion headless on OHOS/CI. The test therefore stages the full
runtime shared-library closure (copied + ELF-signed, mirroring the libxft/
clxclient OHOS pattern), then runs a shell smoke test that asserts each
binary loads its closure and reaches its normal early-exit path.
"""

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv


class AlikiTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "test_aliki.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        if not can_run(self):
            raise ConanException("aliki target consumers are not runnable")
        bin_dir = self._package_bin_dir()
        runtime_root = str(Path(self.build_folder, "runtime-libs"))
        self.output.info(f"ALIKI_TEST_RUNTIME_PATH={runtime_root}")
        if str(self.settings.os) == "OHOS":
            self._prepare_ohos_runtime(runtime_root)
            for name in ("aliki", "aliki-rt"):
                binary = os.path.join(bin_dir, name)
                self._sign_ohos_elf(binary)
        script = os.path.join(self.source_folder, "test_aliki.sh")
        os.chmod(script, (os.stat(script).st_mode & 0o777) | 0o755)
        if str(self.settings.os) == "OHOS":
            self.run(
                f'LD_LIBRARY_PATH="{runtime_root}" "{script}" "{bin_dir}"',
                env="conanrun",
            )
        else:
            self.run(f'"{script}" "{bin_dir}"', env="conanrun")

    # ── package layout ───────────────────────────────────────────────────

    def _package_bin_dir(self):
        package = self.dependencies["aliki"]
        for bindir in package.cpp_info.bindirs:
            path = Path(bindir)
            if not path.is_absolute():
                path = Path(package.package_folder, bindir)
            if path.is_dir():
                return str(path)
        raise ConanException("aliki package has no bin directory")

    # ── OHOS runtime closure ─────────────────────────────────────────────

    def _prepare_ohos_runtime(self, runtime_root):
        root = Path(runtime_root)
        # A previous interrupted run may have left the staging directory
        # behind; recreate it cleanly so conan create is idempotent.
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=False, exist_ok=False)
        copied = 0
        for _, dependency in self.dependencies.items():
            if getattr(dependency, "build", False) or getattr(
                dependency, "test", False
            ):
                continue
            if not dependency.package_folder:
                continue
            package_root = Path(dependency.package_folder).resolve(strict=True)
            for libdir in dependency.cpp_info.libdirs:
                source_dir = Path(libdir)
                if not source_dir.is_absolute():
                    source_dir = Path(dependency.package_folder, libdir)
                if not source_dir.is_dir():
                    continue
                for entry in sorted(source_dir.iterdir(), key=lambda item: item.name):
                    if not (entry.name.endswith(".so") or ".so." in entry.name):
                        continue
                    source = entry.resolve(strict=True)
                    if not source.is_file() or source.is_symlink():
                        raise ConanException(
                            f"runtime shared library is not regular: {entry}"
                        )
                    try:
                        source.relative_to(package_root)
                    except ValueError as error:
                        raise ConanException(
                            f"runtime shared library escapes its package: {entry}"
                        ) from error
                    destination = root / entry.name
                    if destination.exists():
                        if destination.is_symlink() or not self._same_bytes(
                            destination, source
                        ):
                            raise ConanException(
                                f"runtime library basename collision: {entry.name}"
                            )
                        continue
                    shutil.copy2(source, destination)
                    shutil.copymode(source, destination)
                    copied += 1
        if copied == 0:
            raise ConanException("OHOS runtime library closure is empty")
        for library in sorted(root.iterdir(), key=lambda item: item.name):
            self._sign_ohos_elf(str(library), force=True)
        return root

    @staticmethod
    def _same_bytes(left, right):
        if left.stat().st_size != right.stat().st_size:
            return False
        with left.open("rb") as left_stream, right.open("rb") as right_stream:
            while True:
                left_block = left_stream.read(1024 * 1024)
                right_block = right_stream.read(1024 * 1024)
                if left_block != right_block:
                    return False
                if not left_block:
                    return True

    def _sign_ohos_elf(self, path, force=False):
        signer = shutil.which("binary-sign-tool") or (
            "/data/service/hnp/bin/binary-sign-tool"
        )
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("required OHOS signing tools are missing")
        existing = subprocess.run(
            [readelf, "-SW", path],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout.count(".codesign")
        if existing == 1 and not force:
            os.chmod(path, (os.stat(path).st_mode & 0o777) | 0o755)
        elif existing not in (0, 1):
            raise ConanException(f"ELF has an invalid .codesign count: {path}")
        else:
            objcopy = shutil.which("llvm-objcopy") or (
                "/data/service/hnp/bin/llvm-objcopy"
            )
            if existing == 1 and not os.path.isfile(objcopy):
                raise ConanException("required OHOS objcopy is missing")
            unsigned = f"{path}.unsigned"
            temporary = f"{path}.signed"
            for candidate in (unsigned, temporary):
                if os.path.lexists(candidate):
                    raise ConanException(f"stale signing output exists: {candidate}")
            sign_input = path
            try:
                if existing == 1:
                    shutil.copy2(path, unsigned)
                    subprocess.run(
                        [objcopy, "--remove-section", ".codesign", unsigned],
                        check=True,
                        timeout=30,
                    )
                    sign_input = unsigned
                subprocess.run(
                    [
                        signer,
                        "sign",
                        "-inFile",
                        sign_input,
                        "-outFile",
                        temporary,
                        "-selfSign",
                        "1",
                    ],
                    check=True,
                    stdout=sys.stderr,
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
                    raise ConanException(f"signed ELF has invalid .codesign: {path}")
                os.chmod(temporary, (os.stat(path).st_mode & 0o777) | 0o755)
                os.replace(temporary, path)
            finally:
                for candidate in (temporary, unsigned):
                    if os.path.lexists(candidate):
                        os.unlink(candidate)
        final_sections = subprocess.run(
            [readelf, "-SW", path],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if (
            final_sections.count(".codesign") != 1
            or not stat.S_IMODE(os.stat(path).st_mode) & stat.S_IXUSR
        ):
            raise ConanException(f"final signed ELF validation failed: {path}")
