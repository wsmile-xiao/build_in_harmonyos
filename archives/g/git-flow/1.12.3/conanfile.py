#!/usr/bin/env python3
"""Conan recipe for git-flow 1.12.3 — pure Shell script project.

git-flow (AVH Edition) is a collection of Git extensions providing high-level
repository operations for Vincent Driessen's branching model.
It is a pure Shell script project with no compilation step; "installation"
consists of running `make install` which copies scripts to bin/ and hooks
to share/doc/gitflow/hooks/.

Platform adaptations for OHOS:
  1. E098: OHOS toybox lacks the `install` command; patch Makefile to use
     `cp + chmod` instead of `install -d -m` / `install -m`.
  2. Shebangs use #!/bin/sh which is available on OHOS via toybox — no fix needed.

R28: test_package/ exists.
R32: No os-conditional code needed.
R34: test_package runs `git-flow version` to verify the installed package.
R38: commands.json declared at software level (tool type).
"""
import os
import stat

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class GitflowConan(ConanFile):
    name = "git-flow"
    version = "1.12.3"
    description = "A collection of Git extensions to provide high-level repository operations for Vincent Driessen's branching model"
    license = "BSD-2-Clause"
    homepage = "https://github.com/petervanderdoes/gitflow-avh"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Apply E098 patch: replace `install` command with `cp + chmod`
        apply_conandata_patches(self)

    def package(self):
        # Run `make install` in source folder to copy scripts and hooks
        self.run(f'make -C "{self.source_folder}" install prefix="{self.package_folder}"')

    def package_info(self):
        # Pure script project: executables in bin/, no libraries
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
