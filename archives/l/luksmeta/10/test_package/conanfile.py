#!/usr/bin/env python3
"""Consumer tests for luksmeta 10 on HarmonyOS PC."""

import json
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class LuksmetaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _runtime_view(self):
        view = os.path.join(self.build_folder, "ohos-runtime-libs")
        os.makedirs(view, exist_ok=True)
        for dependency in self.dependencies.values():
            if not dependency.package_folder:
                continue
            cpp_info = dependency.cpp_info.aggregated_components()
            for libdir in cpp_info.libdirs:
                source_dir = os.path.join(dependency.package_folder, libdir)
                if not os.path.isdir(source_dir):
                    continue
                for filename in os.listdir(source_dir):
                    if ".so" not in filename or filename.endswith(".la"):
                        continue
                    source = os.path.join(source_dir, filename)
                    if not os.path.isfile(source):
                        continue
                    destination = os.path.join(view, filename)
                    if not os.path.exists(destination):
                        shutil.copy2(os.path.realpath(source), destination)
        return view

    def _run_test(self, name, runtime_view, tmpdir):
        executable = os.path.join(self.build_folder, "bin", name)
        runner = self.conf.get(
            "user.luksmeta:qemu_runner", default="", check_type=str
        ).strip()
        if cross_building(self) and not runner:
            raise ConanInvalidConfiguration(
                "Cross-building luksmeta tests requires user.luksmeta:qemu_runner"
            )
        command = shlex.split(runner) if runner else []
        if runner:
            command.extend([
                "-E", "LD_LIBRARY_PATH=" + runtime_view,
                "-E", "TMPDIR=" + tmpdir,
            ])
        command.append(executable)
        self.run(shlex.join(command), cwd=self.build_folder)

    def test(self):
        runtime_view = self._runtime_view()
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        previous = os.environ.get("LD_LIBRARY_PATH")
        previous_tmpdir = os.environ.get("TMPDIR")
        paths = [runtime_view] + ([previous] if previous else [])
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(paths)
        os.environ["TMPDIR"] = tmpdir
        try:
            self._run_test("test_api", runtime_view, tmpdir)
            self._run_test("test_ohos", runtime_view, tmpdir)
        finally:
            if previous is None:
                os.environ.pop("LD_LIBRARY_PATH", None)
            else:
                os.environ["LD_LIBRARY_PATH"] = previous
            if previous_tmpdir is None:
                os.environ.pop("TMPDIR", None)
            else:
                os.environ["TMPDIR"] = previous_tmpdir

        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "test_api && test_ohos",
            "discovered": 2,
            "passedCount": 2,
        }))
