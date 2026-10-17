#!/usr/bin/env python3
"""Consumer tests for the packaged shed executable.

Two C programs are built with the OHOS toolchain and drive the packaged
bin/shed like a user: through pipes for the command line contract and on a
pseudo terminal (TERM=vt100, terminfo from the ncurses run environment) for
the full-screen editor, checking the rendered screen, exit codes and the
files shed writes.  test_shed_ohos covers the HarmonyOS adaptation: piped
input buffered in $TMPDIR instead of the OHOS musl tmpfile() directory.
"""
import os
import platform
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class ShedTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        shed = os.path.join(self.dependencies["shed"].package_folder, "bin", "shed")
        if not os.path.isfile(shed):
            raise ConanException(f"packaged shed executable missing: {shed}")
        with open(shed, "rb") as handle:
            header = handle.read(20)
        if header[:4] != b"\x7fELF" or header[18:20] != b"\xb7\x00":
            raise ConanException("packaged shed is not an AArch64 ELF")
        # can_run() is also true on the x86 runner (binfmt, build == host
        # profile), but the dynamically linked OHOS executable needs
        # /lib/ld-musl-aarch64.so.1 there (E544): the pty tests execute on
        # the aarch64 OHOS builder only.
        if platform.machine() not in ("aarch64", "arm64"):
            self.output.warning("x86 runner: shed pty consumer tests are executed on the "
                                "aarch64 OHOS builder, not here")
            return
        work = os.path.join(self.build_folder, "shed-test-work")
        shutil.rmtree(work, ignore_errors=True)
        os.makedirs(work)
        for name in ("test_shed_consumer", "test_shed_ohos"):
            executable = os.path.join(self.build_folder, name)
            if self.settings.os == "OHOS":
                self._sign_ohos_elf(executable)
            self.run(f'"{executable}" "{shed}" "{work}"', env="conanrun")

    def _sign_ohos_elf(self, path):
        # E077/E077B: re-sign freshly linked test executables before running
        # them; the signer must not see the buildenv LD_LIBRARY_PATH.
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        if not (os.path.isfile(signer) and os.path.isfile(objcopy)):
            self.output.warning(f"signing tools not found, running {path} unsigned")
            return
        env = {k: v for k, v in os.environ.items() if k != "LD_LIBRARY_PATH"}
        signed = path + ".signed"
        subprocess.run([objcopy, "--remove-section", ".codesign", path],
                       check=True, env=env, timeout=60)
        subprocess.run([signer, "sign", "-inFile", path, "-outFile", signed, "-selfSign", "1"],
                       check=True, env=env, timeout=120)
        os.replace(signed, path)
        os.chmod(path, 0o755)
