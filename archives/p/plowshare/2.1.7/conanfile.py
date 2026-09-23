#!/usr/bin/env python3
"""Conan recipe — plowshare 2.1.7.

plowshare is a pure Bash script suite (6 CLI tools + core.sh). There is no
C/C++ compilation step: packaging copies the scripts into bin/ (flat layout,
because each tool sources "$(dirname $0)/core.sh"), injects the release
version, and validates syntax / --help / --version at build and test time.
"""
import os
import shutil
import stat

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

VERSION_MARKER = "declare -r VERSION='GIT-snapshot'"
VERSION_REPLACEMENT = "declare -r VERSION='2.1.7'"


class PlowshareConan(ConanFile):
    name = "plowshare"
    version = "2.1.7"
    description = "Command-line tool suite and engine for managing file-sharing websites"
    license = "GPL-3.0"
    homepage = "https://github.com/mcrapet/plowshare"
    url = "https://github.com/mcrapet/plowshare"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    generators = "VirtualBuildEnv"

    cli_tools = {
        "plowdown": "download.sh",
        "plowup": "upload.sh",
        "plowdel": "delete.sh",
        "plowlist": "list.sh",
        "plowprobe": "probe.sh",
        "plowmod": "mod.sh",
    }

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def configure(self):
        self.settings.rm_safe("os.version")

    def requirements(self):
        # 不声明 bash：它是系统工具（HarmonyOS 上位于 PATH，如 /data/service/hnp/bin），
        # 运行时由系统提供，同 prettyping 先例。
        self.requires("curl/8.15.0")
        self.requires("openssl/3.5.6.1.1", override=True)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _bash(self):
        for candidate in (
            os.environ.get("CONFIG_SHELL"),
            shutil.which("bash"),
            "/data/service/hnp/bin/bash",
            os.environ.get("SHELL"),
        ):
            if candidate and os.path.exists(candidate):
                return candidate
        return "bash"

    def _inject_version(self, script_path):
        with open(script_path, "r", encoding="utf-8") as fh:
            content = fh.read()
        if VERSION_MARKER not in content:
            raise RuntimeError(
                f"VERSION marker not found in {script_path}; "
                "upstream layout may have changed"
            )
        content = content.replace(VERSION_MARKER, VERSION_REPLACEMENT)
        with open(script_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)

    def build(self):
        apply_conandata_patches(self)

        bash = self._bash()

        for target in ("core.sh",) + tuple(self.cli_tools.values()):
            script = os.path.join(self.source_folder, "src", target)
            if not os.path.exists(script):
                raise RuntimeError(f"missing source script: {script}")
            self.run(f'"{bash}" -n "{script}"')

        for target in self.cli_tools.values():
            script = os.path.join(self.source_folder, "src", target)
            self._inject_version(script)

        self.run(
            f'PLOWSHARE_FORCE_VERSION=2.1.7 "{bash}" -n '
            f'"{os.path.join(self.source_folder, "scripts", "version")}" || true'
        )

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)

        src_dir = os.path.join(self.source_folder, "src")
        copy(self, "core.sh", src=src_dir, dst=bin_dir)
        for cli, upstream in self.cli_tools.items():
            copy(self, upstream, src=src_dir, dst=bin_dir, keep_path=False)
            renamed = os.path.join(bin_dir, cli)
            os.replace(os.path.join(bin_dir, upstream), renamed)
            st = os.stat(renamed)
            os.chmod(renamed, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        modules_dir = os.path.join(self.package_folder, "share", "plowshare", "modules")
        os.makedirs(modules_dir, exist_ok=True)
        copy(self, "config", src=os.path.join(src_dir, "modules"),
             dst=modules_dir, keep_path=False)

        man1_dir = os.path.join(self.package_folder, "share", "man", "man1")
        man5_dir = os.path.join(self.package_folder, "share", "man", "man5")
        os.makedirs(man1_dir, exist_ok=True)
        os.makedirs(man5_dir, exist_ok=True)
        for man in ("plowdown.1", "plowup.1", "plowdel.1", "plowlist.1",
                    "plowprobe.1", "plowmod.1"):
            copy(self, man, src=os.path.join(self.source_folder, "docs"),
                 dst=man1_dir, keep_path=False)
        copy(self, "plowshare.conf.5", src=os.path.join(self.source_folder, "docs"),
             dst=man5_dir, keep_path=False)
        copy(self, "plowshare.conf.sample",
             src=os.path.join(self.source_folder, "docs"),
             dst=os.path.join(self.package_folder, "share", "doc", "plowshare"),
             keep_path=False)

        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []