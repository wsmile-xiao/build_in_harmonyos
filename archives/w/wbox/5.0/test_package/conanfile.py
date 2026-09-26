#!/usr/bin/env python3
"""Conan test_package — wbox 5.0 (HarmonyOS PC / aarch64).

R34: both scripts below really execute the packaged `wbox` binary, nothing is
stubbed or print-only:

  test.sh            client-side smoke test (version banner + usage)
  test_wbox_ohos.sh  HarmonyOS-specific verification — upstream ships no test
                     suite at all, so this is the layer that proves the tool
                     actually works on OHOS:
                       T1 ELF64 AArch64 / PIE
                       T2 musl loader, no glibc linkage
                       T3 no host build path leaked into the binary
                       T4 non-executable stack (NX)
                       T5 end-to-end servermode + client: HTTP 200 with body
                          match, 404 for missing file, fork()-based concurrent
                          clients, connection-refused exit code 3
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class WboxTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        wbox_bin = os.path.join(self.dependencies["wbox"].package_folder,
                                "bin", "wbox")
        bash = os.environ.get("CONFIG_SHELL", "bash")
        for script in ("test.sh", "test_wbox_ohos.sh"):
            self.run(f'"{bash}" "{os.path.join(self.source_folder, script)}" '
                     f'"{wbox_bin}"', env="conanrun")
