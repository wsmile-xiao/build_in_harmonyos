#!/usr/bin/env python3
"""Conan recipe — seqprep 1.3.2.

jstjohn/SeqPrep: overlapping paired-end FASTQ read merger/adapter trimmer
(C99 command-line tool).  Upstream GitHub tag v1.3.2.

OHOS adaptations:
  - raw Makefile build: CC comes from Conan conf (R33), make -j1 (E074);
  - links -lz -lm: zlib provided by the conan dependency (include/lib dirs
    injected through the Makefile's COPTS/CFLAGS/LDFLAGS knobs);
  - upstream Test/RUNTEST.sh is patched for portability (0001: /bin/sh,
    zcat, python3, output dirs) and executed in build() as the L1 upstream
    test — see conandata.yml patch_description and the PR 修改说明;
  - package_type = application: the SeqPrep executable is installed to bin/,
    commands.json declares the CLI (R38).
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class SeqprepConan(ConanFile):
    name = "seqprep"
    version = "1.3.2"
    description = ("SeqPrep - adapter trimming and merging of overlapping "
                   "paired-end FASTQ reads")
    license = "MIT"
    homepage = "https://github.com/jstjohn/SeqPrep"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # house convention: system-name deps are published without
        # user/channel on the ohpcd remote (152 recipes use plain ref)
        self.requires("zlib/1.3.1")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "seqprep is only supported on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # R33: compiler from Conan conf, never from shell env.  Some conan
        # builds reject the subkey access (settings-only profile merge), so
        # fall back to the plain toolchain name (PATH-resolved, same as
        # AutotoolsToolchain emits).
        try:
            cc = self.conf.get("tools.build:compiler_executables:c", "clang",
                               check_type=str)
        except Exception:
            cc = "clang"
        zcpp = self.dependencies["zlib"].cpp_info
        zinc = zcpp.includedirs[0]
        zlibs = zcpp.libdirs[0]
        # Raw Makefile: upstream CFLAGS hardcodes '-c -Wall -O0 -g -std=c99';
        # override with release flags + zlib include.  E074: -j1.
        make_cmd = (
            "make -j1 CC=" + shlex.quote(cc)
            + " COPTS=" + shlex.quote("-I" + zinc)
            + " CFLAGS=" + shlex.quote("-c -O2 -std=c99 -Wall")
            + " LDFLAGS=" + shlex.quote("-L" + zlibs + " -lz -lm")
        )
        self.run(make_cmd, cwd=self.source_folder, env="conanbuild")
        # L1: upstream test script (portability-patched by 0001): runs two
        # real SeqPrep merge/trim jobs on bundled gz FASTQ data and builds
        # read-length histograms from the outputs.  The script expects its
        # own directory as cwd (../SeqPrep, ./out, ./info, seqlens.py).
        self.run("mkdir -p out info && sh RUNTEST.sh",
                 cwd=os.path.join(self.source_folder, "Test"),
                 env="conanbuild")

    def package(self):
        copy(self, "SeqPrep", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
