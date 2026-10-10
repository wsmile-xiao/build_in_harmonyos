#!/usr/bin/env python3
"""Consumer test for ttysnoop 0.12d (HarmonyOS PC / OHOS aarch64).

``test_ttysnoop.c`` is compiled with the host toolchain and then drives the
*packaged* ``ttysnoops`` / ``ttysnoop`` binaries end to end: ttysnoops is
started on a pty the way getty/telnetd would start it, runs the test binary as
the snooped login program on a UNIX98 pty and mirrors the session to a second
pty; the ttysnoop client is exercised on its error paths and, where the
filesystem allows AF_UNIX sockets, against the server socket.
"""
import os
import platform
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.layout import basic_layout


class TtysnoopTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        # R33: the C compiler comes from the profile conf, not from ${CC}.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = (compilers or {}).get("c") or "cc"
        src = os.path.join(self.source_folder, "test_ttysnoop.c")
        out = os.path.join(self.build_folder, "test_ttysnoop")
        self.run(
            f"{shlex.quote(cc)} -O2 -Wall -o {shlex.quote(out)} {shlex.quote(src)}"
        )

    def test(self):
        bindir = os.path.join(
            self.dependencies[self.tested_reference_str].package_folder, "bin"
        )
        tools = [os.path.join(bindir, name) for name in ("ttysnoops", "ttysnoop")]
        harness = os.path.join(self.build_folder, "test_ttysnoop")
        for path in tools + [harness]:
            if not os.path.isfile(path):
                raise ConanException(f"missing executable: {path}")

        if str(self.settings.arch) == "armv8" and platform.machine() not in (
            "aarch64",
            "arm64",
        ):
            # Dynamically linked OHOS executables cannot start on an x86_64
            # build machine (no aarch64 musl loader); the consumer test runs
            # on the aarch64 device.
            self.output.warning(
                "test_ttysnoop built for armv8 but NOT executed on this "
                f"{platform.machine()} build machine"
            )
            return

        if str(self.settings.os) == "OHOS":
            self._sign_ohos_elf(harness)
        self.run(
            f"{shlex.quote(harness)} {shlex.quote(tools[0])} {shlex.quote(tools[1])}",
            cwd=self.build_folder,
            env="conanrun",
        )

    @staticmethod
    def _sign_ohos_elf(path):
        """OHOS only executes ELF files carrying a code signature; ttysnoops
        also executes this binary as its login program."""
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            raise ConanException("binary-sign-tool is required to run the test on OHOS")
        signed = path + ".signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", signed, "-selfSign", "1"],
            check=True,
            timeout=120,
        )
        os.chmod(signed, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(signed, path)
