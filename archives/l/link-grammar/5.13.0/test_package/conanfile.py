#!/usr/bin/env python3
"""Conan consumer test for Link Grammar 5.13.0."""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import load, save


class LinkGrammarTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("Cross build: consumer compiled and linked")
            return
        executable = os.path.join(self.cpp.build.bindir, "test_link_grammar")
        package_folder = self.dependencies["link-grammar"].package_folder
        data_dir = os.path.join(
            package_folder,
            "share",
            "link-grammar",
        )
        self.run(
            "%s %s" % (shlex.quote(executable), shlex.quote(data_dir)),
            env="conanrun",
        )
        cli = os.path.join(package_folder, "bin", "link-parser")
        self.run("%s --version" % shlex.quote(cli), env="conanrun")

        sentence_file = os.path.join(self.build_folder, "sentence.txt")
        cli_output = os.path.join(self.build_folder, "link-parser.out")
        save(self, sentence_file, "This is a test.\n")
        english_dictionary = os.path.join(data_dir, "en")
        self.run(
            "%s %s '-!batch' < %s > %s"
            % (
                shlex.quote(cli),
                shlex.quote(english_dictionary),
                shlex.quote(sentence_file),
                shlex.quote(cli_output),
            ),
            env="conanrun",
        )
        output = load(self, cli_output)
        if "Found " not in output or " linkages" not in output:
            raise ConanException("link-parser did not report a parsed linkage")
        self.output.info("link-parser parsed the sentence in batch mode")
