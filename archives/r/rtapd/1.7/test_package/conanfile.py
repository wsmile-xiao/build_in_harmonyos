#!/usr/bin/env python3
"""test_package — HarmonyOS consumer test for the packaged rtapd/vsnppd binaries.

`check_rtapd.c` is a real consumer-side client: it plays the role of rtnppd and
hands rtapd a TNPP packet over the daemon's external queue socket
(`ExtSocketIn`), using the wire format and CRC-16 that rtapd itself emits.
`test.sh` boots the packaged daemon in a self-contained sandbox and drives the
whole chain (socket -> TNPP parse -> CAP page -> route lookup -> file device).
"""
import os

from conan import ConanFile


class RtapdTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        comp = self.conf.get("tools.build:compiler_executables", check_type=dict, default={})
        cc = comp.get("c", "clang") if comp else "clang"
        src = os.path.join(self.source_folder, "check_rtapd.c")
        out = os.path.join(self.build_folder, "check_rtapd")
        self.run(f"'{cc}' -O2 -Wall -o '{out}' '{src}'")

    def test(self):
        bindir = os.path.join(self.dependencies["rtapd"].package_folder, "bin")
        for exe in ("rtapd", "vsnppd"):
            path = os.path.join(bindir, exe)
            assert os.path.isfile(path), f"{exe} binary not found in package: {path}"

        # A build host that cannot run aarch64 OHOS binaries at all cannot run
        # this test (not a package defect): report an explicit skip instead.
        import platform
        if (platform.machine().lower() not in ("aarch64", "arm64")
                and not os.path.exists("/lib/ld-musl-aarch64.so.1")):
            with open(os.path.join(bindir, "rtapd"), "rb") as f:
                head = f.read(20)
            assert head[:4] == b"\x7fELF" and head[18:20] == b"\xb7\x00", "rtapd is not an aarch64 ELF"
            self.output.warning("SKIPPED test.sh: host cannot execute aarch64 OHOS binaries "
                                "(no /lib/ld-musl-aarch64.so.1); only ELF/aarch64 header checked")
            return

        # OHOS /system/bin/sh (mksh) cannot be relied upon to execute ELF
        # binaries, so prefer a real bash.  CONFIG_SHELL is only accepted when it
        # actually points at bash (the OHOS profile sets it to the HNP bash, but
        # G0/clean-verify exports CONFIG_SHELL=/bin/sh on the same host).
        bash = os.environ.get("CONFIG_SHELL", "")
        if os.path.basename(bash) != "bash":
            bash = "/data/service/hnp/bin/bash"
            if not os.path.isfile(bash):
                bash = "bash"
        script = os.path.join(self.source_folder, "test.sh")
        check = os.path.join(self.build_folder, "check_rtapd")
        self.run(f"'{bash}' '{script}' '{check}' '{bindir}'", env="conanrun")
