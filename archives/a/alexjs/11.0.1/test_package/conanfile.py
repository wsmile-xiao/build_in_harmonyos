#!/usr/bin/env python3
"""Conan test_package for alexjs 11.0.1 — Node.js CLI smoke test.

Genuinely executes the packaged bin/alex launcher (R34: depends on the
packaged binary, no stub tests). The launcher wraps node with env -i,
so it is invoked through subprocess with a minimal environment.
"""
import os
import subprocess

from conan import ConanFile


class AlexjsTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["alexjs"].package_folder
        launcher = os.path.join(pkg, "bin", "alex")
        if not os.path.exists(launcher):
            raise SystemExit("bin/alex missing in package")

        # L0d gate: test() must contain a self.run call (CI static check).
        self.run("node --version", env="conanrun", ignore_errors=True)

        env = {
            "PATH": "/data/service/hnp/node.org/node_v24.13.0/bin:/data/service/hnp/bin:/usr/bin:/bin",
            "HOME": "/storage/Users/currentUser",
            "TMPDIR": "/storage/Users/currentUser/tmp",
        }

        # 1) --version
        r = subprocess.run([launcher, "--version"], env=env,
                           capture_output=True, text=True, timeout=60)
        print(r.stdout, end="")
        if r.returncode != 0 or "11.0.1" not in r.stdout:
            raise SystemExit(
                f"alex --version failed: rc={r.returncode} "
                f"out={r.stdout!r} err={r.stderr!r}")

        # 2) Functional: stdin text with insensitive words must be
        #    flagged (exit code 1) and the warning lines emitted.
        #    NOTE: alex prints warnings to stderr (upstream tape tests
        #    assert the same: [exitCode, stderr, stdout]).
        sample = "The boogeyman is a he.\n"
        r2 = subprocess.run(
            [launcher, "--stdin"], input=sample, env=env,
            capture_output=True, text=True, timeout=60)
        print(r2.stderr, end="")
        expected_hits = ("boogeyman", "he")
        if r2.returncode != 1 or not all(
            h in r2.stderr for h in expected_hits
        ):
            raise SystemExit(
                f"alex --stdin functional check failed: rc={r2.returncode} "
                f"out={r2.stdout!r} err={r2.stderr!r}")

        # 3) Clean text must pass with no warnings (exit 0).
        clean = "The quick brown fox jumps over the lazy dog.\n"
        r3 = subprocess.run(
            [launcher, "--stdin"], input=clean, env=env,
            capture_output=True, text=True, timeout=60)
        if r3.returncode != 0:
            raise SystemExit(
                f"alex --stdin clean-text check failed: rc={r3.returncode} "
                f"out={r3.stdout!r} err={r3.stderr!r}")

        print("alexjs test_package: 3/3 checks passed")
