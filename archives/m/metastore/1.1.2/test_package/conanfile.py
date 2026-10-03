#!/usr/bin/env python3
"""test_package for metastore 1.1.2.

Consumer verification: execute the packaged `metastore` binary the way a user
would and assert real, observable results — its exit status, its own --dump
rendering, and the on-disk metadata it restores.  No echo/print stubs.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


def _shell():
    """A shell that can actually exec our aarch64 OHOS binaries.

    OHOS ships mksh as /system/bin/sh, and it cannot exec ELF binaries, so
    the assertions have to be driven through bash.  CI runs on a real
    HarmonyOS device where bash lives at /data/service/hnp/bin/bash (and
    the ohos-aarch64 profile exports CONFIG_SHELL to point there); a local
    WSL cross build has plain /bin/bash instead.  Pick the first candidate
    that actually exists rather than hard-coding either one — the rdate
    1.11 recipe hard-codes the device path, which breaks every non-device
    build; hard-coding /bin/bash breaks CI (exactly what build #66656 hit:
    "/system/bin/sh: /bin/bash: inaccessible or not found").
    """
    candidates = []
    env = os.environ.get("CONFIG_SHELL")
    if env:
        candidates.append(env)
    candidates += [
        "/data/service/hnp/bin/bash",   # HarmonyOS device (CI worker)
        "/bin/bash",                    # generic Linux (local cross builds)
    ]
    for c in candidates:
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return "bash"  # last resort: let the OS resolve it from PATH


class MetastoreTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test_metastore.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        bash = _shell()
        self.output.info(f"metastore test shell: {bash}")
        script = os.path.join(self.source_folder, "test_metastore.sh")
        self.run(f'"{bash}" "{script}"', env="conanrun")
