#!/usr/bin/env python3
"""Conan test_package for jnoisemeter 0.4.1 — packaged-tool smoke test.

jnoisemeter is an X11 GUI client of a running JACK server, so it cannot run to
completion headless on OHOS/CI. The test therefore stages the full runtime
shared-library closure (copied + ELF-signed, mirroring the libxft/clxclient/
aliki OHOS pattern), then runs a shell smoke test that asserts the binary loads
its closure and reaches a normal upstream early-exit path: `-h` prints the
jnoisemeter-0.4.1 banner, and a run without DISPLAY returns 1 rather than 127.
"""

import os
import shutil
import stat
import subprocess
import sys
import uuid
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv


class JnoisemeterTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "test_jnoisemeter.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        if not can_run(self):
            raise ConanException("jnoisemeter target consumers are not runnable")
        bin_dir = self._package_bin_dir()
        runtime_root = self._new_runtime_staging_dir()
        self.output.info(f"JNOISEMETER_TEST_RUNTIME_PATH={runtime_root}")
        if str(self.settings.os) == "OHOS":
            self._prepare_ohos_runtime(runtime_root)
            for name in ("jnoisemeter",):
                binary = os.path.join(bin_dir, name)
                self._sign_ohos_elf(binary)
        script = os.path.join(self.source_folder, "test_jnoisemeter.sh")
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
        package = self.dependencies["jnoisemeter"]
        for bindir in package.cpp_info.bindirs:
            path = Path(bindir)
            if not path.is_absolute():
                path = Path(package.package_folder, bindir)
            if path.is_dir():
                return str(path)
        raise ConanException("jnoisemeter package has no bin directory")

    # ── OHOS runtime closure ─────────────────────────────────────────────

    # ── per-run staging location ───────────────────────────────────────

    STAGING_PREFIX = "jnoisemeter-runtime-"

    def _staging_base(self):
        """Disposable root that holds the per-run staging dir.

        TMPDIR/TMP/TEMP are honoured; the documented fallback is $HOME/tmp,
        the project-wide disposable artifact area.  Nothing here ever points
        back into the PR archive directory.
        """
        for var in ("TMPDIR", "TMP", "TEMP"):
            value = os.environ.get(var)
            if value and os.path.isdir(value):
                return value
        home_tmp = os.path.join(os.path.expanduser("~"), "tmp")
        Path(home_tmp).mkdir(parents=True, exist_ok=True)
        return home_tmp

    def _new_runtime_staging_dir(self):
        """Create a fresh staging dir OUTSIDE the archive, unique per run.

        Two defects fixed here (W5 audit round 1, face 11):
          * the closure used to be staged at build_folder/runtime-libs, i.e.
            inside archives/j/jnoisemeter/0.4.1/test_package/, where a
            directory-wide `git add` once swept 114 .so files into a commit;
          * that path was fixed, and _prepare_ohos_runtime() wiped and
            re-created it, so the framework's second `conan test` for the
            same test_package overwrote the first run's closure.

        `mktemp -d` is deliberately NOT used: HMDFS rewrites its 0700 mode
        into a directory the euid cannot write into, so the mode is applied
        explicitly below.  There is no fallback into the package directory:
        if staging cannot be created the build goes red.
        """
        base = self._staging_base()
        nonce = "%d-%s" % (os.getpid(), uuid.uuid4().hex[:12])
        root = Path(base, self.STAGING_PREFIX + nonce)
        try:
            root.mkdir(parents=True, exist_ok=False)
        except OSError as error:
            raise ConanException(
                "cannot create OHOS runtime staging dir %s: %s" % (root, error)
            ) from error
        os.chmod(root, (os.stat(root).st_mode & 0o777) | 0o755)
        resolved = root.resolve(strict=True)
        archive = Path(self.recipe_folder).resolve(strict=True)
        if resolved == archive or archive in resolved.parents:
            raise ConanException(
                "OHOS runtime staging must not live inside the archive: %s" % resolved
            )
        return str(resolved)

    def _prepare_ohos_runtime(self, runtime_root):
        # runtime_root was created fresh and uniquely for this run by
        # _new_runtime_staging_dir(), so nothing is wiped here: the unique
        # suffix is exactly what stops two `conan test` invocations from
        # clobbering each other's closure.
        root = Path(runtime_root)
        if not root.is_dir():
            raise ConanException(
                "OHOS runtime staging dir is missing: %s" % runtime_root
            )
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
