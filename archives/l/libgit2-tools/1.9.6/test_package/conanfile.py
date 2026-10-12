#!/usr/bin/env python3
"""Conan test_package for libgit2-tools — verifies the git2 binary works."""
import os
import shutil
import tempfile

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class Libgit2ToolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # R34: test must actually exercise the built git2 binary.
        bin_path = os.path.join(
            self.dependencies[self.tested_reference_str].package_folder,
            "bin",
            "git2",
        )
        # Run `git2 --version` to verify the binary executes.
        self.run(f'"{bin_path}" --version', env=["conanrun"])

        # Also run the compiled consumer test (test_git2), which validates
        # both --version and an end-to-end `git2 init` repository creation.
        # GIT2_BIN tells it where the packaged binary lives.
        # GIT2_TEST_DIR points at a local-filesystem scratch dir: HMDFS
        # worktrees may carry uid-0 stat results that fail libgit2's
        # repository-ownership check during `git2 init`.
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_git2")
        workdir = tempfile.mkdtemp(prefix="git2-init-")
        try:
            env = f'GIT2_BIN="{bin_path}" GIT2_TEST_DIR="{workdir}"'
            self.run(f"{env} \"{test_bin}\"", env=["conanrun"])
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
