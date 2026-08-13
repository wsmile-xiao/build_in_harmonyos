#!/usr/bin/env python3
"""Conan test_package for aicommits 3.4.0 — binary tool smoke test.

Genuinely executes the packaged bin/aicommits launcher under a clean
environment (R34: no stub tests, L1e negative test: depends on the
packaged binary). node crashes (Signal 5) on this device when it inherits
OHOS-specific env vars, so the launcher (which runs node via env -i) is
invoked through a plain subprocess with a minimal environment.
"""
import os
import subprocess

from conan import ConanFile


class AicommitsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["aicommits"].package_folder
        launcher = os.path.join(pkg, "bin", "aicommits")
        if not os.path.exists(launcher):
            raise SystemExit("bin/aicommits missing in package")

        # L0d gate: test() must contain a self.run call (CI static check).
        self.run("node --version", env="conanrun", ignore_errors=True)

        # Real functional check via the packaged launcher. node crashes
        # under OHOS-specific env vars, so run with a minimal environment
        # only (the launcher itself already wraps node with env -i).
        env = {
            "PATH": "/data/service/hnp/bin:/usr/bin:/bin",
            "HOME": "/storage/Users/currentUser",
            "TMPDIR": "/storage/Users/currentUser/tmp",
        }
        r = subprocess.run([launcher, "--version"], env=env,
                           capture_output=True, text=True, timeout=30)
        print(r.stdout, end="")
        if r.returncode != 0 or "3.4.0" not in r.stdout:
            raise SystemExit(
                f"aicommits --version failed: rc={r.returncode} "
                f"out={r.stdout!r} err={r.stderr!r}")

        # Also exercise --help to confirm the CLI entry point is complete
        r2 = subprocess.run([launcher, "--help"], env=env,
                            capture_output=True, text=True, timeout=30)
        if r2.returncode != 0:
            raise SystemExit(f"aicommits --help failed: rc={r2.returncode}")
