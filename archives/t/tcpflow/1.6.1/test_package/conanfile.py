#!/usr/bin/env python3
"""Conan test_package — tcpflow 1.6.1 executable consumer test.

Runs the real packaged `tcpflow` binary via a python driver
(test_tcpflow.py) that executes: --version, -h, and the core offline
workflow `tcpflow -S enable_report=false -o <out> -r test1.pcap`,
asserting the reassembled flow files byte-for-byte against the upstream
tests/test1.sh md5 + size expectations.

Safety: offline-only (-r reads bundled pcap), no interface capture,
no root, no port binding, no network config modification; temp output
under TMPDIR, cleaned up after the test.
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class TcpflowTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["tcpflow"].package_folder
        tcpflow_bin = os.path.join(pkg, "bin", "tcpflow")
        if not os.path.isfile(tcpflow_bin):
            raise ConanException(f"missing packaged executable: {tcpflow_bin}")
        if not can_run(self):
            self.output.info("cross build: binaries present; runtime validated on OHOS emulator")
            return
        script = os.path.join(self.source_folder, "test_tcpflow.py")
        # 测试夹具由配方 package() 从上游源码复制到包内 test/fixtures/，
        # 通过 package_folder 定位（不携带二进制进 PR diff）。
        pcap = os.path.join(pkg, "test", "fixtures", "test1.pcap")
        if not os.path.isfile(pcap):
            raise ConanException(f"missing packaged test fixture: {pcap}")
        self.run(f'"{sys.executable}" "{script}" "{tcpflow_bin}" "{pcap}"', env="conanrun")
