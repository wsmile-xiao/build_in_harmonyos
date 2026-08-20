#!/usr/bin/env python3
"""Conan recipe for the prebuilt ai-cli 0.4.2 npm application."""

import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.layout import basic_layout


class AiCliConan(ConanFile):
    name = "ai-cli"
    version = "0.4.2"
    description = "Agent-oriented CLI for generating text, images, video, and audio"
    license = "Apache-2.0"
    homepage = "https://github.com/vercel-labs/ai-cli"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("ai", "cli", "nodejs", "generative-ai")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"ai-cli is prepared for Linux/OHOS targets only, got {self.settings.os}"
            )
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("ai-cli supports OHOS armv8 only")

        node = shutil.which("node")
        if not node:
            raise ConanInvalidConfiguration("ai-cli requires Node.js >= 22 in PATH")
        try:
            result = subprocess.run(
                [node, "--version"], check=True, capture_output=True,
                text=True, timeout=15,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise ConanInvalidConfiguration(f"unable to execute Node.js: {exc}") from exc
        match = re.match(r"^v(\d+)", result.stdout.strip())
        if not match or int(match.group(1)) < 22:
            raise ConanInvalidConfiguration(
                f"ai-cli requires Node.js >= 22, found {result.stdout.strip()!r}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        entry = os.path.join(self.source_folder, "dist", "index.js")
        wasm = os.path.join(self.source_folder, "dist", "openh264-d6yed0d8.wasm")
        for required in (entry, wasm, os.path.join(self.source_folder, "package.json")):
            if not os.path.isfile(required):
                raise ConanException(f"required npm release artifact is missing: {required}")

        node_flags = "--jitless" if str(self.settings.os) == "OHOS" else ""
        # OHOS Node v24 traps in V8 JIT initialization for this bundle. Jitless
        # mode is deterministic for the CLI's offline text/help paths.
        self.run(f'node {node_flags} "{entry}" --version')
        self.run(f'node {node_flags} "{entry}" --help')

    def package(self):
        app_dir = os.path.join(self.package_folder, "libexec", "ai-cli")
        copy(self, "*", src=os.path.join(self.source_folder, "dist"),
             dst=os.path.join(app_dir, "dist"), keep_path=True)
        copy(self, "package.json", src=self.source_folder, dst=app_dir, keep_path=False)
        copy(self, "README.md", src=self.source_folder, dst=app_dir, keep_path=False)

        shell = "/system/bin/sh" if str(self.settings.os) == "OHOS" else "/bin/sh"
        node_flags = "--jitless " if str(self.settings.os) == "OHOS" else ""
        launcher = os.path.join(self.package_folder, "bin", "ai")
        launcher_body = "\n".join(
            (
                f"#!{shell}",
                "set -eu",
                'script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)',
                f'exec node {node_flags}"$script_dir/../libexec/ai-cli/dist/index.js" "$@"',
                "",
            )
        )
        save(self, launcher, launcher_body)
        os.chmod(launcher, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
