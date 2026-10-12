#!/usr/bin/env python3
"""Conan test_package for kingfisher 1.109.0 — consumer-view functional test.

R34: this test really runs the packaged ``kingfisher`` binary and asserts on
observed behaviour (version, real detection of synthetic credentials, clean
input, loaded rule engine) via ``test.sh``. It is never a print-only stub.

OHOS notes:
  * /system/bin/sh (mksh) cannot execute ELF binaries here; use bash explicitly.
  * libgit2/openssl from the Harmonybrew prefix must be on LD_LIBRARY_PATH,
    because the musl loader ignores DT_RUNPATH.
"""
import os

from conan import ConanFile


class KingfisherTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R32: only meaningful on the ported platforms.
        if self.settings.os not in ("Linux", "OHOS"):
            return

        binary = os.path.join(
            self.dependencies["kingfisher"].package_folder, "bin", "kingfisher")
        assert os.path.isfile(binary), f"kingfisher binary not found at {binary}"

        # The OHOS loader ignores DT_RUNPATH, so expose the Harmonybrew libs
        # (libgit2.so.1.9, libssl/libcrypto) explicitly. Copied into the
        # process environment: in Conan 2 `self.run(..., env="conanrun")` runs
        # the command through the conanrun script and DROPS the `env=` dict
        # (verified: KINGFISHER_BIN was empty inside test.sh), so the variables
        # the script needs must already be in os.environ.
        os.environ["KINGFISHER_BIN"] = binary
        brew_lib = os.path.expanduser("~/.harmonybrew/lib")
        if os.path.isdir(brew_lib):
            os.environ["LD_LIBRARY_PATH"] = (
                brew_lib + ":" + os.environ.get("LD_LIBRARY_PATH", ""))

        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries; wrap with bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'{bash} test.sh')
