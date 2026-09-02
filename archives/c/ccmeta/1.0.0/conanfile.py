#!/usr/bin/env python3
"""Conan recipe — ccmeta 1.0.0 (shell skill, no compile)"""

import json
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class CcmetaConan(ConanFile):
    name = "ccmeta"
    version = "1.0.0"
    description = "Let Claude Code drive its own meta commands via tmux — Agent Skill framework"
    license = "MIT"
    homepage = "https://github.com/Alfredvc/ccmeta"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("claude-code", "tmux", "agent-skill", "shell")
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def build(self):
        if self.settings.os not in ("Linux", "OHOS"):
            self.output.warning("ccmeta is a shell skill, OS check is advisory only")
        apply_conandata_patches(self)
        core = os.path.join(self.source_folder, "shared", "ccmeta-core.sh")
        if os.path.exists(core):
            self.run(f'sh -n "{core}"')
        # HMBS machine evidence: upstream has no test suite (shell skill framework, no tests/ dir,
        # no Makefile/CMake test target). Emit no_tests marker so first build (non-cached) passes
        # evidence gate; cache-hit rounds are covered by test_package re-emit.
        upstream = {
            "status": "no_tests",
            "framework": "shell",
            "command": "",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "Upstream is a Claude Code Agent Skill framework (shell + markdown), not a compiled library; no test suite provided. Audited source (26e7b1d): only skills/*.md, shared/*.sh, demo/*.tape/gif, hooks/pre-commit, scripts/sync-shared.sh — no tests/ dir, no Makefile/CMake test target, no TEST/TEST_F/def test_."
        }
        msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
        # print for hmbs stdout scan and self.output for conan log
        print(msg, flush=True)
        self.output.info(msg)

    def package(self):
        copy(self, "*.sh", src=os.path.join(self.source_folder, "shared"), dst=os.path.join(self.package_folder, "share", "ccmeta", "shared"))
        copy(self, "*.sh", src=os.path.join(self.source_folder, "skills", "ccmeta"), dst=os.path.join(self.package_folder, "share", "ccmeta", "skills", "ccmeta"))
        copy(self, "*.sh", src=os.path.join(self.source_folder, "skills", "ccmeta-dangerous"), dst=os.path.join(self.package_folder, "share", "ccmeta", "skills", "ccmeta-dangerous"))
        copy(self, "*.md", src=os.path.join(self.source_folder, "skills", "ccmeta"), dst=os.path.join(self.package_folder, "share", "ccmeta", "skills", "ccmeta"))
        copy(self, "*.md", src=os.path.join(self.source_folder, "skills", "ccmeta-dangerous"), dst=os.path.join(self.package_folder, "share", "ccmeta", "skills", "ccmeta-dangerous"))
        copy(self, "README.md", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "ccmeta"))
        copy(self, "CLAUDE.md", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "ccmeta"))
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        wrapper = os.path.join(bin_dir, "ccmeta")
        with open(wrapper, "w", encoding="utf-8", newline="\n") as f:
            f.write("#!/bin/sh\n")
            f.write('echo "ccmeta 1.0.0 — shared/ccmeta-core.sh installed under $0/../share/ccmeta"\n')
            f.write('ls "$(dirname "$0")/../share/ccmeta/shared/ccmeta-core.sh" >/dev/null 2>&1 && echo "core: OK" || echo "core: missing"\n')
        try:
            os.chmod(wrapper, 0o755)
        except Exception:
            pass

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
