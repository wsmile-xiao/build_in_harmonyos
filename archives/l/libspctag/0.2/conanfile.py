#!/usr/bin/env python3
"""Conan recipe — libspctag 0.2 (CMake)."""

import json
import os
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LibspctagConan(ConanFile):
    name = "libspctag"
    version = "0.2"
    description = "C library for reading and writing ID666 metadata in SPC files"
    license = "GPL-3.0-or-later"
    homepage = "https://sourceforge.net/projects/libspctag/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = "spc", "id666", "snes", "metadata"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libspctag supports Linux and OHOS, not %s" % self.settings.os
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        toolchain.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        if str(self.settings.os) == "OHOS":
            toolchain.cache_variables["CMAKE_SYSTEM_NAME"] = "OHOS"
            toolchain.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8"
                else str(self.settings.arch)
            )
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])
        self._run_upstream_test()

    def _run_upstream_test(self):
        """Compile and run upstream's sole test/test.c sample unchanged."""
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compiler_executables.get("c") or shutil.which("clang") or shutil.which("cc")
        if not cc:
            raise ConanException("C compiler not available for upstream test/test.c")

        build_dir = Path(self.build_folder)
        lib_dir = build_dir / "src"
        test_binary = build_dir / "libspctag_upstream_test"
        fixture = build_dir / "upstream-test.spc"

        data = bytearray(256)
        data[:27] = b"SNES-SPC700 Sound File Data"
        data[35] = 26
        for offset, value in (
            (46, b"Upstream test"),
            (158, b"12/31/1999"),
            (169, b"180"),
            (172, b"0500"),
        ):
            data[offset:offset + len(value)] = value
        fixture.write_bytes(bytes(data))

        compile_cmd = [
            str(cc),
            str(Path(self.source_folder) / "test" / "test.c"),
            "-I" + str(Path(self.source_folder) / "src"),
            "-L" + str(lib_dir),
            "-lspctag",
            "-Wl,-rpath," + str(lib_dir),
            "-o",
            str(test_binary),
        ]
        compile_result = subprocess.run(
            compile_cmd,
            cwd=self.build_folder,
            env=os.environ.copy(),
            capture_output=True,
            text=True,
        )
        if compile_result.stdout:
            self.output.info(compile_result.stdout)
        if compile_result.stderr:
            self.output.info(compile_result.stderr)
        if compile_result.returncode != 0:
            raise ConanException("failed to compile upstream test/test.c")

        run_env = os.environ.copy()
        old_ld_path = run_env.get("LD_LIBRARY_PATH", "")
        run_env["LD_LIBRARY_PATH"] = (
            str(lib_dir) + os.pathsep + old_ld_path if old_ld_path else str(lib_dir)
        )
        run_result = subprocess.run(
            [str(test_binary), str(fixture)],
            cwd=self.build_folder,
            env=run_env,
            capture_output=True,
            text=True,
        )
        if run_result.stdout:
            self.output.info(run_result.stdout)
        if run_result.stderr:
            self.output.info(run_result.stderr)
        if run_result.returncode != 0:
            raise ConanException(
                "upstream test/test.c failed with exit %d" % run_result.returncode
            )
        if "Version : 0.2" not in run_result.stdout:
            raise ConanException("upstream test/test.c did not report libspctag 0.2")
        if run_result.stdout.count("Song title : Upstream test") != 2:
            raise ConanException(
                "upstream test/test.c did not restore the original title"
            )

        marker = {
            "status": "passed",
            "framework": "upstream-sample",
            "command": "./libspctag_upstream_test upstream-test.spc",
            "discovered": 1,
            "executed": 1,
            "passed": 1,
            "failed": 0,
            "skipped": 0,
        }
        marker_line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker)
        self.output.info(marker_line)
        (build_dir / "upstream_test_result.json").write_text(
            json.dumps(marker, indent=2) + "\n", encoding="utf-8"
        )

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "upstream_test_result.json",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "res"),
        )

    def package_info(self):
        self.cpp_info.libs = ["spctag"]
        self.cpp_info.set_property("cmake_file_name", "libspctag")
        self.cpp_info.set_property("cmake_target_name", "libspctag::spctag")
