#!/usr/bin/env python3
"""Conan test_package for abuild 3.17.0.

abuild is a CLI tool set for Alpine Linux. The C helper tools (abuild-tar,
abuild-gzsplit, abuild-sudo, abuild-fetch, abuild-rm, abuild-rmtemp) are
ELF binaries that can be verified on OHOS. The shell scripts (abuild,
abuild-keygen, etc.) require Alpine runtime (apk-tools) and are not
testable on OHOS.
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class AbuildTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["abuild"]
        bindir = os.path.join(dep.package_folder, "bin")

        # 1. Verify C helper tools exist — fail if any missing (R34: must depend on package)
        c_tools = ["abuild-tar", "abuild-gzsplit", "abuild-sudo",
                    "abuild-fetch", "abuild-rm", "abuild-rmtemp"]
        for tool in c_tools:
            tool_path = os.path.join(bindir, tool)
            if not os.path.isfile(tool_path):
                raise ConanException(f"Required C helper tool not found: {tool}")
            self.output.info(f"  {tool}: {os.path.getsize(tool_path)} bytes")

        # 2. Verify shell scripts exist
        scripts = ["abuild", "abuild-keygen", "abuild-sign",
                    "newapkbuild", "abump", "apkgrel", "checkapk"]
        for script in scripts:
            script_path = os.path.join(bindir, script)
            if not os.path.isfile(script_path):
                self.output.warning(f"  {script}: not found (shell script, non-critical)")
            else:
                self.output.info(f"  {script}: {os.path.getsize(script_path)} bytes")

        # 3. Run abuild-tar (ELF binary) to verify it can execute without crash
        abuild_tar = os.path.join(bindir, "abuild-tar")
        result = self.run(f"{abuild_tar} 2>&1",
                          env="conanrun", ignore_errors=True)
        if result >= 128 or result == 127:
            raise ConanException(
                f"abuild-tar crashed (exit code {result}): "
                "possible missing shared library"
            )
        self.output.info("abuild-tar: runs without crash")

        # 4. Run abuild-sudo (setuid C helper) to verify predictable behavior on OHOS.
        #    abuild-sudo is designed to elevate to root for whitelisted commands
        #    (adduser/addgroup/apk/abuild-rmtemp). On OHOS the "abuild" group and
        #    those paths do not exist, so it must fail with a controlled error
        #    (exit 1: "Group not found"/"Not a valid subcommand") rather than
        #    crash or fail to load. The recipe installs it WITHOUT the setuid bit
        #    (0o755) since OHOS does not support setuid root elevation.
        abuild_sudo = os.path.join(bindir, "abuild-sudo")
        result = self.run(f"{abuild_sudo} 2>&1",
                          env="conanrun", ignore_errors=True)
        if result >= 128 or result == 127:
            raise ConanException(
                f"abuild-sudo crashed (exit code {result}): "
                "possible missing shared library"
            )
        if result != 1:
            self.output.info(f"abuild-sudo: exited {result} (expected controlled error on OHOS)")
        else:
            self.output.info("abuild-sudo: controlled failure (exit 1) as expected on OHOS")