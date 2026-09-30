#!/usr/bin/env python3
"""Conan test_package for cfm (Cactus File Manager).

Consumer perspective: a higher-layer app shells out to the installed `cfm`
binary as its runtime artifact. We verify:
  1. The installed binary exists on PATH and starts on a real directory
     (non-interactive run with closed stdin must exit 0, proving the ELF
     loads and the directory scan runs on the target).
  2. A C consumer (test.c) is compiled with the toolchain, then fork+execs
     the installed binary against a real directory and asserts a clean exit.
  3. Under a pseudo-terminal the TUI actually renders (escape sequences
     are emitted) and quits cleanly with 'q'.
"""
import os
import pty
import select
import tempfile
import time

from conan import ConanFile
from conan.tools.layout import basic_layout


class CfmTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        # Compile the C consumer against the installed package env.
        # R33: get the compiler from Conan conf, never from shell env vars.
        comp = self.conf.get("tools.build:compiler_executables", default={},
                             check_type=dict)
        cc = comp.get("c") or "clang"
        src = os.path.join(self.source_folder, "test.c")
        self.run(f"{cc} {src} -o consumer_test")

    def test(self):
        pkg_folder = None
        for dep in self.dependencies.values():
            if dep.ref.name == "cfm":
                pkg_folder = dep.package_folder
                break
        assert pkg_folder, "cfm dependency package folder not found"
        binpath = os.path.join(pkg_folder, "bin", "cfm")
        assert os.path.isfile(binpath), f"installed binary missing: {binpath}"

        # 1) Non-interactive smoke: cfm <dir> with closed stdin must exit 0.
        with tempfile.TemporaryDirectory() as d:
            probe = os.path.join(d, "probe-file.txt")
            with open(probe, "w") as f:
                f.write("consumer-probe\n")
            self.run(f"cfm {d} </dev/null >/dev/null 2>&1", env="conanrun")

        # 2) C consumer: fork+exec the installed binary (compiled in build()).
        self.run("./consumer_test", env="conanrun")

        # 3) PTY-driven TUI check: render output must contain escape sequences
        #    (alternative screen buffer) and quit with 'q' must exit 0.
        workdir = tempfile.mkdtemp(prefix="cfm-consumer-")
        with open(os.path.join(workdir, "visible.txt"), "w") as f:
            f.write("pty-render-check\n")
        pid, fd = pty.fork()
        if pid == 0:
            os.execv(binpath, [binpath, workdir])
            os._exit(127)
        out = b""
        deadline = time.time() + 15
        sent = False
        rc = -1
        try:
            while time.time() < deadline:
                r, _, _ = select.select([fd], [], [], 0.3)
                if r:
                    try:
                        chunk = os.read(fd, 4096)
                    except OSError:
                        break
                    if not chunk:
                        break
                    out += chunk
                if not sent and b"\x1b[" in out:
                    os.write(fd, b"q")  # quit TUI
                    sent = True
            done, status = os.waitpid(pid, os.WNOHANG)
            if not done:
                done, status = os.waitpid(pid, 0)
            rc = os.waitstatus_to_exitcode(status) if done else -1
        finally:
            os.close(fd)
        assert rc == 0, f"cfm pty run failed: rc={rc}"
        assert b"\x1b[" in out, "cfm did not render a TUI under pty"
        print(f"PASS: cfm consumer: pty TUI rendered ({len(out)} bytes), quit rc={rc}")
