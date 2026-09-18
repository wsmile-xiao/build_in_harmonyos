#!/usr/bin/env python3
"""test_package for mmsrip 0.7.0 — CLI smoke + protocol checks on-device.

The assertions live in mmsrip_cli_checks.py (the test source file); this
conanfile runs it against the installed binary via self.run(), with the
conanrun environment applied. See mmsrip_cli_checks.py for the rationale
behind every expectation (all derived from the upstream 0.7.0 sources).

Coverage summary:
  1. -v/--version, -a/--about, -h/--help banners (exit 0)
  2. no arguments → usage, exit 1
  3. http:// URL rejected pre-socket, exit 1
  4. mms:// URL without a path rejected, exit 1
  5. -t against an unresolvable host: real DNS/socket failure path,
     exit 1, no output file created
  6. -g debug log created and filled (run fails with usage, exit 1)
  7. OHOS-specific ELF check: dynamic ELF64 LE EM_AARCH64 with the
     musl /lib/ld-musl-aarch64.so.1 PT_INTERP
"""
import os

from conan import ConanFile
from conan.tools.build import build_jobs
from conan.tools.env import VirtualRunEnv


class MmsripTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass  # nothing to compile — this package ships only a binary

    def test(self):
        dep = self.dependencies.get(self.tested_reference_str)
        mmsrip = os.path.join(dep.package_folder, "bin", "mmsrip")
        assert os.path.isfile(mmsrip), f"mmsrip missing at {mmsrip}"

        checks = os.path.join(self.source_folder, "mmsrip_cli_checks.py")
        assert os.path.isfile(checks), f"test source missing: {checks}"

        # self.run() with the VirtualRunEnv applied and failing exit codes
        # propagated (raise_policy) — the whole point of this package.
        self.run(
            f'python3 "{checks}" "{mmsrip}"',
            env="conanrun",
            cwd=self.build_folder,
        )
        self.output.success("mmsrip test_package passed")
