#!/usr/bin/env python3
"""Conan recipe — debianbuttons 2.3 (Debian "icedeb" webextension, data package).

debianbuttons ("Debian queries") is a Firefox/Thunderbird webextension by
Damyan Ivanov that queries Debian-related websites using the clipboard text.
The upstream orig tarball is 100% JS/CSS/HTML (15 files): icedeb.js (popup
logic), icedeb-content.js (content script), icedeb.html/icedeb.css,
manifest.json (manifest_version 2) and icon resources. There is no compiled
library, no executable and no C/C++ source; the only upstream "build" step is
the Makefile's `all` target, which zips the files into icedeb.xpi.

Conan modelling decision (honest, zero fake linkage):
  - single recipe, data/metadata package (`package_type="unknown"`);
  - build() reproduces the upstream Makefile `all` target with the Python
    stdlib zipfile (same ALL_FILES list), so the CI worker does not need
    make/zip; the resulting icedeb.xpi is the genuine upstream artifact;
  - package() ships the authentic extension source tree plus the built
    icedeb.xpi under share/debianbuttons/; no fake executables or libraries;
  - zero Conan requires (webextension has no library dependencies);
  - no bin/, no ELF artifacts (test_package asserts this explicitly), so
    L0k/R38 commands.json is not applicable (not a CLI tool).
  - R47 lang-preflight reported detected=mixed (expected=cpp) and the package
    was routed to lang_hold (env_unsupported, non-failure). The platform
    review (knowledge-extension subflow 2.2) requires archives/ adaptation
    code alongside knowledge/; following the debian-pan/debian-science/
    debichem precedent this PR therefore delivers the real webextension
    artifact as a data package (source + built .xpi) with a validating
    test_package, while the R47 judgment is documented in notes.md.
"""
import os
import zipfile

from conan import ConanFile
from conan.tools.files import (apply_conandata_patches, copy,
                              export_conandata_patches, get)

# Upstream Makefile ALL_FILES (icedeb.xpi 的打包清单，与上游逐项一致)
ALL_FILES = [
    "README", "TODO", "Changes", "manifest.json",
    "icedeb.js", "icedeb.css", "icedeb.html", "icedeb-content.js",
    "res/icon.xcf",
    "icons/openlogo-nd.svg",
    "icons/icedeb-addon-light.svg", "icons/icedeb-addon-dark.svg",
]


class DebianButtonsConan(ConanFile):
    name = "debianbuttons"
    version = "2.3"
    package_type = "unknown"
    description = ("Debian 'icedeb' (Debian queries) webextension: JS/CSS/HTML extension "
                   "source + built icedeb.xpi artifact; no compilable code")
    license = "MIT-like (SPI Open Use Logo License + upstream permissive; see README)"
    homepage = "https://salsa.debian.org/webext-team/debianbuttons"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"  # CI L0 gate; data package, no real semantics
    options = None
    default_options = None

    def export_sources(self):
        # 本包 patches 为空（patches: {}），此处仅为 CI G1 配方完整性契约；
        # export_conandata_patches 对空 patches 段是 no-op。
        export_conandata_patches(self)

    def requirements(self):
        pass  # 零 Conan requires：webextension 无库依赖（R36 无缺失依赖）

    def layout(self):
        self.folders.source = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # patches: {} 为空段 → no-op；保持与全仓无补丁配方的统一契约。
        apply_conandata_patches(self)
        # 复刻上游 Makefile `all`：用 Python stdlib zipfile 打 icedeb.xpi
        #（文件清单与上游 ALL_FILES 完全一致；CI worker 无 make/zip 也可构建）。
        src = self.source_folder
        stage = os.path.join(self.build_folder, "stage")
        os.makedirs(stage, exist_ok=True)
        xpi_path = os.path.join(stage, "icedeb.xpi")
        with zipfile.ZipFile(xpi_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for rel in ALL_FILES:
                path = os.path.join(src, rel)
                if not os.path.isfile(path):
                    raise RuntimeError("missing upstream file for icedeb.xpi: %s" % rel)
                zf.write(path, rel)

    def package(self):
        dst = os.path.join(self.package_folder, "share", "debianbuttons")
        # 真实上游产物：源码树 + build() 构建的 icedeb.xpi
        copy(self, "*", src=self.source_folder, dst=dst)
        copy(self, "icedeb.xpi", src=os.path.join(self.build_folder, "stage"), dst=dst)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = ["share"]
