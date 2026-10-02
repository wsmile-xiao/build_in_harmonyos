#!/usr/bin/env python3
"""test_package - sredird 2.2.2 (OHOS consumer test).

sredird has no library API, so the consumer is a small C program
(rfc2217_client.c) that is compiled here with the OHOS toolchain through
CMake and then runs the packaged bin/sredird as an RFC 2217 server: a
socketpair plays the network connection, a pseudo terminal (posix_openpt)
plays the serial port, and seven checks cover the Telnet negotiation, the
lock file, both data directions with IAC escaping, and the termios changes
(baud rate, stop bits, flow control) that sredird applies to the serial
device on client request. It exits non-zero on the first failed check.

The binary path comes from the tested package only (no PATH lookup), so the
CI L1e destructive check fails once bin/ is removed. Running needs an aarch64
host with the OHOS musl loader: the Conan profile used for host and build is
the same, so can_run() is always true and cannot tell an x86_64 runner apart;
on such a host (no /lib/ld-musl-aarch64.so.1) the run is reported as SKIPPED,
never as passed. Where the OHOS signing tools exist, both the consumer and the
copy of sredird used for the run are self-signed first (build folder copies,
the package itself is not modified).
"""
import os
import platform
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class SredirdTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # The tested package must ship the tool on every host (also the foreign-
        # architecture one), otherwise the test fails.
        packaged = os.path.join(self.dependencies["sredird"].package_folder, "bin", "sredird")
        if not os.path.isfile(packaged):
            raise ConanException(f"bin/sredird missing from the tested package: {packaged}")
        if not self._host_can_execute():
            self.output.warning(
                "SKIPPED: rfc2217_client was cross-built for aarch64 OHOS but this host "
                "cannot execute it (needs aarch64 and /lib/ld-musl-aarch64.so.1); "
                "the functional check runs on the aarch64 CI worker"
            )
            return
        client = os.path.join(self.build_folder, self.cpp.build.bindir, "rfc2217_client")
        server = os.path.join(self.build_folder, "sredird-under-test")
        shutil.copy2(packaged, server)
        if str(self.settings.os) == "OHOS":
            for path in (client, server):
                self._sign_ohos_elf(path)
        self.run(f'"{client}" "{server}"', cwd=self.build_folder, env="conanrun")

    def _host_can_execute(self):
        if not can_run(self):
            return False
        if str(self.settings.arch) != "armv8":
            return True
        return (platform.machine().lower() in ("aarch64", "arm64")
                and os.path.exists("/lib/ld-musl-aarch64.so.1"))

    def _sign_ohos_elf(self, path):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(path):
            raise ConanException(f"Missing OHOS executable to sign: {path}")
        if not os.path.isfile(signer) or not os.path.isfile(objcopy):
            self.output.warning(f"OHOS signing tools not found, running {path} unsigned")
            return
        subprocess.run([objcopy, "--remove-section", ".codesign", path], check=True, timeout=30)
        subprocess.run([signer, "sign", "-inFile", path, "-outFile", path, "-selfSign", "1"],
                       check=True, timeout=60)
        os.chmod(path, (os.stat(path).st_mode & 0o777) | 0o055)
