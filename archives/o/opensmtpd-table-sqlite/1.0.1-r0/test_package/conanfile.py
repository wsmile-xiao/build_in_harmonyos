#!/usr/bin/env python3
"""Conan test_package for opensmtpd-table-sqlite.

Verifies the sqlite3 transitive dependency is functional by building
and running a C program that creates an in-memory SQLite database,
inserts data, and queries it back.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class OpensmtpdTableSqliteTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("sqlite3/3.49.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # Also verify the installed table-sqlite binary exists and runs
        dep = self.dependencies["opensmtpd-table-sqlite"]
        binary = os.path.join(str(dep.package_folder), "libexec", "smtpd", "table-sqlite")
        assert os.path.isfile(binary), f"table-sqlite binary not found at {binary}"
        self.run(f'"{binary}" --nonexistent-config 2>&1; test $? -ne 0')
