#!/usr/bin/env python3
"""Conan test package for the zls executable.

Runs test.sh which performs, from the consumer point of view:
  1. `zls --version` must print 0.15.1 — executing the ELF at all proves the
     OHOS code-signing (package() self-sign) is accepted by the kernel.
  2. `zls env` must resolve its config/log paths via known-folders under the
     OHOS HOME layout.
  3. The packaged zls must be a static aarch64 ELF (pure-Zig product, no
     host .so closure — the OHOS adaptation keeps the binary self-contained).
  4. A real LSP stdio session: initialize -> initialized -> shutdown -> exit
     with JSON-RPC Content-Length framing, asserting the server answers
     id:1 with capabilities. This exercises the threaded stdio transport,
     JSON layer and the actual server loop on OHOS.
"""

import os

from conan import ConanFile


class ZlsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution (flow-control paradigm).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
