#!/usr/bin/env python3
"""Conan test_package for photopc 3.07.

Upstream ships no test suite (N_static=0), so this consumer test exercises
the packaged binaries' real behavior with assertions (see consumer_test.py):
epinfo version banner, file-parsing path, usage, and photopc's
device-open/termios error path.
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class PhotopcTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: compile/link test only")
            return

        dep = self.dependencies["photopc"]
        bindir = self._absolute_paths(dep.package_folder, dep.cpp_info.bindirs or ["bin"])[0]
        outdir = os.path.join(self.build_folder, "_consumer_out")
        shutil.rmtree(outdir, ignore_errors=True)
        os.makedirs(outdir, exist_ok=True)
        # Work on copies: signing mutates the file, so never touch the
        # packaged originals inside the read-only package folder.
        binaries = []
        for name in ("photopc", "epinfo"):
            dst = os.path.join(outdir, name)
            shutil.copy2(os.path.join(bindir, name), dst)
            os.chmod(dst, 0o755)
            binaries.append(dst)
        if self.settings.os == "OHOS":
            for dst in binaries:
                self._sign_executable(dst)

        script = os.path.join(self.source_folder, "consumer_test.py")
        self.run(
            'python3 %s %s %s' % (
                shlex.quote(script), shlex.quote(outdir), shlex.quote(outdir)
            ),
            env="conanrun",
        )

    # ── helpers ─────────────────────────────────────────────────────────
    def _absolute_paths(self, package_folder, dirs):
        return [
            path if os.path.isabs(path) else os.path.join(package_folder, path)
            for path in dirs
        ]

    def _find_ohos_tool(self, name, aliases=()):
        for tool in (name,) + tuple(aliases):
            resolved = shutil.which(tool)
            if resolved:
                return resolved
        for directory in (
            "/data/service/hnp/bin",
            "/storage/Users/currentUser/usr/local/bin",
        ):
            for tool in (name,) + tuple(aliases):
                candidate = os.path.join(directory, tool)
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    return candidate
        return name

    def _sign_executable(self, path):
        objcopy = self._find_ohos_tool("llvm-objcopy", aliases=("objcopy",))
        signer = self._find_ohos_tool("binary-sign-tool")
        temporary = f"{path}.unsigned"
        shutil.copy2(path, temporary)
        self.run(
            "{} --remove-section .codesign {} 2>/dev/null || true".format(
                shlex.quote(objcopy), shlex.quote(temporary)
            )
        )
        self.run(
            shlex.join(
                [signer, "sign", "-selfSign", "1", "-signAlg", "SHA256withECDSA",
                 "-inFile", temporary, "-outFile", path]
            )
        )
        if os.path.isfile(path):
            os.chmod(path, 0o755)
        if os.path.isfile(temporary):
            os.remove(temporary)
