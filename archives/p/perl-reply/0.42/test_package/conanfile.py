#!/usr/bin/env python3
"""Conan test_package for perl-reply 0.42 — Perl smoke test.

Verifies that:
1. Reply.pm and bundled dependencies are properly packaged
2. reply --version works (L2 smoke test)
3. reply --help works
4. Core Perl modules can be loaded via PERL5LIB
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.build import can_run


class PerlReplyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            dep = self.dependencies["perl-reply"]
            perl5lib = os.path.join(dep.package_folder, "lib", "perl5")
            reply_pm = os.path.join(perl5lib, "Reply.pm")
            reply_bin = os.path.join(dep.package_folder, "bin", "reply")

            # 1. Verify Reply.pm exists in the package
            assert os.path.exists(reply_pm), \
                f"Reply.pm not found at {reply_pm}"
            self.output.info(f"Reply.pm found at {reply_pm}")

            # 2. Count all .pm files in the package (Reply + bundled deps)
            pm_count = 0
            for root, dirs, files in os.walk(perl5lib):
                for f in files:
                    if f.endswith(".pm"):
                        pm_count += 1
            self.output.info(f"Found {pm_count} .pm files in package")
            assert pm_count >= 30, \
                f"Expected >=30 .pm files (Reply + deps), got {pm_count}"

            # 3. Verify key bundled dependencies exist
            key_deps = [
                "Module/Runtime.pm",
                "Try/Tiny.pm",
                "Config/INI/Reader/Ordered.pm",
                "File/HomeDir.pm",
                "Package/Stash.pm",
                "Eval/Closure.pm",
            ]
            for dep_path in key_deps:
                full_path = os.path.join(perl5lib, dep_path)
                assert os.path.exists(full_path), \
                    f"Dependency {dep_path} not found in package"
            self.output.info("All key dependencies verified")

            # 4. L2 smoke test: reply --version
            assert os.path.exists(reply_bin), \
                f"reply binary not found at {reply_bin}"
            env = os.environ.copy()
            env["PERL5LIB"] = perl5lib
            env["PERL_PARAMS_UTIL_PP"] = "1"
            env["PACKAGE_STASH_IMPLEMENTATION"] = "PP"

            result = subprocess.run(
                ["perl", reply_bin, "--version"],
                capture_output=True, text=True, env=env, timeout=30
            )
            if result.returncode != 0:
                self.output.error(f"reply --version failed: {result.stderr}")
                raise Exception("reply --version smoke test failed")
            assert "Reply version 0.42" in result.stdout, \
                f"Unexpected --version output: {result.stdout}"
            self.output.info(f"reply --version: {result.stdout.strip()}")

            # 5. L2 smoke test: reply --help
            result = subprocess.run(
                ["perl", reply_bin, "--help"],
                capture_output=True, text=True, env=env, timeout=30
            )
            if result.returncode != 0:
                self.output.error(f"reply --help failed: {result.stderr}")
                raise Exception("reply --help smoke test failed")
            assert "reply" in result.stdout, \
                f"Unexpected --help output: {result.stdout}"
            self.output.info(f"reply --help: {result.stdout.strip()}")

            # 6. L2 functional test: REPL evaluation (-l non-interactive mode)
            result = subprocess.run(
                ["perl", reply_bin, "-l"],
                input="1 + 2\n",
                capture_output=True, text=True, env=env, timeout=15
            )
            assert "3" in result.stdout, \
                f"REPL eval failed: stdout={result.stdout}, stderr={result.stderr}"
            self.output.info(f"reply -l REPL eval: PASS (1+2=3)")

            # 7. L2 functional test: module loading in REPL
            result = subprocess.run(
                ["perl", reply_bin, "-l"],
                input="use Data::Dumper\n",
                capture_output=True, text=True, env=env, timeout=15
            )
            assert result.returncode == 0, \
                f"REPL module load failed: {result.stderr}"
            self.output.info("reply -l module loading: PASS")

            self.output.info("Perl smoke test PASSED")
