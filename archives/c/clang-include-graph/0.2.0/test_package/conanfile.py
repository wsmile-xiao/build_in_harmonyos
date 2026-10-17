#!/usr/bin/env python3
"""Conan test_package — clang-include-graph 0.2.0 consumer smoke test.

Runs the *packaged* tool:
  1. `--version` banner smoke (proves the signed binary starts and that its
     Boost/log + libclang DT_NEEDED libraries resolve at load time), and
  2. a real libclang parse of a self-contained fixture TU driven by a
     compile_commands.json, asserting the emitted include graph contains the
     expected header-to-header edge.
"""
import inspect
import json
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run


class ClangIncludeGraphTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _fixture_database(self):
        """Write compile_commands.json (libclang CXCompilationDatabase source)
        pointing at the self-contained fixture TU, return the db dir."""
        source = self.source_folder
        fixture = os.path.join(source, "fixture")
        include_dir = os.path.join(fixture, "headers")
        translation_unit = os.path.join(fixture, "main.cpp")
        db_dir = self.build_folder
        entry = {
            "directory": db_dir,
            "command": "clang++ -std=c++14 "
                       f"-I{include_dir} -c {translation_unit}",
            "file": translation_unit,
        }
        with open(
            os.path.join(db_dir, "compile_commands.json"),
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump([entry], handle)
        return db_dir

    def test(self):
        if not can_run(self):
            self.output.warning(
                "Cross-built tool cannot run on the build host."
            )
            return

        package = self.dependencies[self.tested_reference_str].package_folder
        binary = os.path.join(package, "bin", "clang-include-graph")
        if not os.path.isfile(binary):
            raise ConanInvalidConfiguration(
                f"packaged tool not found: {binary}"
            )

        # 1. Version banner: the process starts and loads every DT_NEEDED
        #    library (boost shared libs via the conan run env, libclang.so via
        #    the SDK RPATH baked at link time).
        self._run_and_check(f'"{binary}" --version', "0.2.0")

        # 2. Real libclang parse of the fixture TU through the packaged tool.
        db_dir = self._fixture_database()
        self._run_and_check(
            f'"{binary}" -d "{db_dir}" -J 1 --tree', "graph_beta.h"
        )

    def _run_and_check(self, command, needle):
        out_file = os.path.join(self.build_folder, "smoke.out")
        self._run_fail_closed(
            f'{command} > "{out_file}" 2>&1', env="conanrun"
        )
        with open(out_file, encoding="utf-8", errors="replace") as handle:
            content = handle.read()
        if needle not in content:
            raise ConanInvalidConfiguration(
                f"expected {needle!r} in tool output; got:\n{content}"
            )
        self.output.info(f"smoke OK: output contains {needle!r}")

    def _run_fail_closed(self, command, **kwargs):
        parameters = inspect.signature(self.run).parameters
        if "ignore_errors" in parameters:
            kwargs["ignore_errors"] = False
        elif "check" in parameters:
            kwargs["check"] = True
        else:
            raise ConanInvalidConfiguration(
                "Unsupported ConanFile.run API: expected ignore_errors or check"
            )
        self.run(command, **kwargs)
