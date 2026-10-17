#!/usr/bin/env python3
"""Conan recipe — lsusb-laniksj 1.1.9 (pure Bash lsusb clone for macOS).

LanikSJ/lsusb: a single self-contained Bash script (445 lines) that mimics
Linux lsusb on macOS by parsing `system_profiler` text output. Upstream has
no build system, no compiled artifacts and no libusb dependency — Homebrew
simply installs the script. This recipe packages the script, its man page
and license, and verifies it by real execution.

HarmonyOS PC adaptation: the macOS-only probes (system_profiler / sw_vers /
ioreg) do not exist on OHOS; the script degrades gracefully to Linux lsusb
semantics — no filters: exit 0 with an empty device list, VID/PID or
bus/dev filters: exit 1 when nothing matches. No source patch is required.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LsusbLaniksjConan(ConanFile):
    name = "lsusb-laniksj"
    version = "1.1.9"
    description = "lsusb command for macOS — pure Bash script clone of Linux lsusb"
    license = "MIT"
    homepage = "https://laniksj.github.io/lsusb/"
    url = "https://github.com/LanikSJ/lsusb"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _bash(self):
        # The script needs real Bash (shopt extglob); /system/bin/sh (mksh)
        # cannot run it. CI worker keeps bash at /data/service/hnp/bin
        # (not in PATH); on-device bash is in PATH (dehydrated precedent).
        bash = os.environ.get("BASH") or shutil.which("bash")
        if bash:
            return bash
        for candidate in ("/data/service/hnp/bin/bash", "/system/bin/bash",
                          "/usr/local/bin/bash"):
            if os.path.isfile(candidate):
                return candidate
        return "bash"

    def build(self):
        apply_conandata_patches(self)
        script = os.path.join(self.source_folder, "lsusb")
        os.chmod(script, 0o755)
        bash = self._bash()
        # 1) Bash syntax self-check.
        self.run('"%s" -n lsusb' % bash, cwd=self.source_folder)
        # 2) Upstream CI smoke (.github/workflows/lsusb-test.yml runs plain
        #    `./lsusb` on macos-latest) — executed for real here via the
        #    explicit interpreter so it also works where bash is not in PATH.
        self.run('"%s" lsusb' % bash, cwd=self.source_folder)
        # 3) Version smoke: real execution must print the version banner.
        self.run('"%s" lsusb -V | grep -q "lsusb for macOS %s"'
                 % (bash, self.version), cwd=self.source_folder)

    def package_id(self):
        # Pure Bash script: identical payload for every configuration.
        self.info.clear()

    def package(self):
        src = self.source_folder
        copy(self, "lsusb", src=src, dst=os.path.join(self.package_folder, "bin"))
        os.chmod(os.path.join(self.package_folder, "bin", "lsusb"), 0o755)
        copy(self, "lsusb.8", src=os.path.join(src, "man"),
             dst=os.path.join(self.package_folder, "share", "man", "man8"),
             keep_path=False)
        copy(self, "LICENSE", src=src,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README.md", src=src,
             dst=os.path.join(self.package_folder, "share", "doc", "lsusb-laniksj"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
