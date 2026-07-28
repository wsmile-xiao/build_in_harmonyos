#!/usr/bin/env python3
"""Consumer test for sha1dc 1.0.3."""

import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.files import save


class Sha1dcTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = self._resolve_tool(compilers.get("c"), "clang")
        dep = self.dependencies["sha1dc"].cpp_info
        exe = os.path.join(self.build_folder, "test_sha1dc")

        cmd = [cc, os.path.join(self.source_folder, "test.c"), "-o", exe]
        for include_dir in dep.includedirs:
            cmd.append("-I" + include_dir)
        for lib_dir in dep.libdirs:
            cmd.append("-L" + lib_dir)
        for lib in dep.libs:
            cmd.append("-l" + lib)
        for system_lib in dep.system_libs:
            cmd.append("-l" + system_lib)
        self.run(" ".join(shlex.quote(part) for part in cmd))
        self._sign_ohos_binary(exe)
        os.chmod(exe, 0o755)

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile/link test completed")
            return

        exe = os.path.join(self.build_folder, "test_sha1dc")
        self.run(shlex.quote(exe), env="conanrun")

        sample = os.path.join(self.build_folder, "sample.txt")
        save(self, sample, "abc")
        dep = self.dependencies["sha1dc"].cpp_info
        tool = os.path.join(dep.bindirs[0], "sha1dcsum")
        self.run(f"{shlex.quote(tool)} {shlex.quote(sample)}", env="conanrun")

    def _resolve_tool(self, configured, fallback):
        if configured and os.path.exists(configured):
            return configured
        found = shutil.which(fallback)
        if found:
            return found
        if configured:
            bindir = os.path.dirname(configured) if os.path.isabs(configured) else ""
            candidate = os.path.join(bindir, fallback) if bindir else ""
            if candidate and os.path.exists(candidate):
                return candidate
        home_candidate = os.path.join(os.path.expanduser("~"), "usr", "local", "bin", fallback)
        if os.path.exists(home_candidate):
            return home_candidate
        return fallback

    def _sign_ohos_binary(self, path):
        if self.settings.os != "OHOS":
            return
        objcopy = self._resolve_tool(None, "llvm-objcopy")
        signer = self._resolve_tool(None, "binary-sign-tool")
        if not (os.path.exists(objcopy) and os.path.exists(signer)):
            return
        signed = path + ".signed"
        self.run(f"{shlex.quote(objcopy)} --remove-section .codesign {shlex.quote(path)}", quiet=True)
        self.run(
            f"{shlex.quote(signer)} sign -inFile {shlex.quote(path)} "
            f"-outFile {shlex.quote(signed)} -selfSign 1",
            quiet=True,
        )
        os.replace(signed, path)
