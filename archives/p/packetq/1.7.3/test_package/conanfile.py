#!/usr/bin/env python3
"""Conan test_package — packetq 1.7.3 consumer run of the installed tool.

R34/PF3: the test actually EXECUTES the packaged `packetq` binary against a
bundled pcap fixture and asserts the golden result, it does not merely
print.  Fixture: upstream's own pcap/sample.pcap.gz (uncompressed, stored
as sample.pcap.b64 because binary files cannot ride GitCode PR diffs),
so the expected rows are upstream-defined and platform-independent
(cross-checked against homebrew packetq 1.7.3 on macOS, 2026-09-05):
`select count(*) as n from dns` yields exactly 8 rows.
"""

import os

from conan import ConanFile


class PacketqTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        packetq = None
        for dependency in self.dependencies.host.values():
            if dependency.ref.name == "packetq":
                bindirs = dependency.cpp_info.bindirs or ["bin"]
                bindir = bindirs[0]
                if not os.path.isabs(bindir):
                    bindir = os.path.join(dependency.package_folder, bindir)
                packetq = os.path.join(bindir, "packetq")
        if not packetq or not os.path.isfile(packetq):
            raise Exception("packetq binary not found in package bindirs")

        b64 = os.path.join(os.path.dirname(__file__), "sample.pcap.b64")
        script = os.path.join(os.path.dirname(__file__), "test_golden.sh")
        self.run('sh "%s" "%s" "%s"' % (script, packetq, b64),
                 env="conanrun")
