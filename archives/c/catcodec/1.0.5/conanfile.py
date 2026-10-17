#!/usr/bin/env python3
"""Conan recipe for catcodec 1.0.5 — OpenTTD sound-catalogue (.cat) codec CLI.

Tool-type (CLI) application; plain GNU Make build (no autotools/cmake).
The upstream Makefile is CXX/CXXFLAGS driven and generates src/rev.cpp via
findversion.sh, so the compiler is taken from the Conan toolchain conf and
SHELL is forced to the HNP bash (R33: never rely on bare ${CC}/${CXX} shell
variables — they are empty on CI workers).

Tests (test_package/test.sh, 11 cases / 28 assertions):
  - Upstream behaviour reproduced programmatically (5 cases, 16 assertions):
    T1 help/version output; T2 encode 8-bit 11025 Hz WAV -> .cat;
    T3 decode .cat -> byte-identical WAV; T4 16-bit 22050 Hz roundtrip;
    T5 two-sample catalogue decode regenerates .sfo metadata + both WAVs.
  - New error-path / boundary tests (6 cases, 12 assertions): T6 wrong .cat
    extension; T7 missing input file; T8 truncated .cat; T9 corrupt .cat
    header; T10 unsupported WAV sample rate; T11 malformed .sfo line.
  Upstream ships no test suite (no tests/ directory and no check/test target
  in the Makefile); all of the above are programmatic CLI tests.

Verified locally: clean conan create pass (see .ci-result.json in reports/).
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    chmod,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class CatcodecConan(ConanFile):
    name = "catcodec"
    version = "1.0.5"
    description = "catcodec: sample catalogue (sound effect set) encoder/decoder for OpenTTD"
    license = "GPL-2.0-only"
    homepage = "https://www.openttd.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # Raw-make projects build in place; zlib recipe precedent.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler from the Conan toolchain conf, never from shell env.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # OHOS has no usable /bin/sh for make recipes; the Makefile also uses
        # $(shell ...) (findversion.sh + cut) to stamp the version into rev.cpp.
        self.run(f"make -j1 SHELL={bash} CXX={cxx}")

    def package(self):
        copy(self, "catcodec", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        chmod(self, os.path.join(self.package_folder, "bin", "catcodec"), 0o755)

    def package_info(self):
        # Tool package (R38 commands.json): expose bin on PATH for consumers.
        self.cpp_info.bindirs = ["bin"]
        self.buildenv_info.define_path("PATH", os.path.join(self.package_folder, "bin"))
