#!/usr/bin/env python3
"""Conan test_package for pktanon — real end-to-end pcap anonymization (R34).

pktanon is a command-line tool, so this L1 test drives the actual binary:
generate a tiny Ethernet/IPv4/TCP pcap, run `pktanon` with an identity
profile (XML parsed through the statically linked Xerces-C++) and assert the
anonymized output trace is produced and the run reports "anonymization done".
"""
import os

from conan import ConanFile


class PktanonTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) does not reliably run this bash script;
        # use the full bash (CONFIG_SHELL) exactly like other tool packages.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test_pktanon.sh", env="conanrun")
