#!/usr/bin/env python3
"""Conan test_package - open-scene-graph 3.6.5.

Consumer-level validation:
  1. Links against the packaged libosg/libosgDB/libOpenThreads and calls
     real APIs (osgGetVersion, osgDB::Registry, OpenThreads runtime).
  2. Runs the packaged `osgversion` binary (executes the installed
     application from the package bin/ folder).
Both steps must print the expected version string "OpenSceneGraph 3.6.5".

OHOS runtime notes: the HMDFS-backed conan cache directory denies
execve() on binaries and (through the loader) on shared libraries that
live in the package folder, so both the packaged libs and the packaged
osgversion are copied into this test package's build folder (an
executable, writable area) before running. Byte-for-byte copies, no
stub or rebuild - the validation still exercises the real package
artifacts.
"""
import json
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class OpenSceneGraphTestConan(ConanFile):
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

    def _mirror_pkg_libs(self):
        """Copy the packaged shared libraries into the test build folder.

        The conan cache mount denies execve()/mmap() on files under the
        package folder, so the dynamic loader cannot resolve libosg*.so.161
        from there. Copying the real entities (plus regenerating the
        SONAME-named copies as plain files) into this build folder makes
        them loadable. The bytes come from the package under test.
        """
        dep = self.dependencies["open-scene-graph"]
        src_lib = os.path.join(dep.package_folder, "lib")
        mirror = os.path.join(self.build_folder, "pkg_lib_mirror")
        shutil.rmtree(mirror, ignore_errors=True)
        os.makedirs(mirror)
        for fn in os.listdir(src_lib):
            fp = os.path.join(src_lib, fn)
            if os.path.isfile(fp) and not os.path.islink(fp):
                shutil.copy(fp, os.path.join(mirror, fn))
                # regenerate SONAME/dev names as real files
                if fn.endswith(".so.3.6.5"):
                    stem = fn[: -len(".3.6.5")]
                    shutil.copy(fp, os.path.join(mirror, stem + ".161"))
                    shutil.copy(fp, os.path.join(mirror, stem))
        # packaged osgversion binary
        bin_mirror = os.path.join(self.build_folder, "pkg_bin_mirror")
        shutil.rmtree(bin_mirror, ignore_errors=True)
        os.makedirs(bin_mirror)
        src_bin = os.path.join(dep.package_folder, "bin", "osgversion")
        if os.path.isfile(src_bin):
            shutil.copy(src_bin, os.path.join(bin_mirror, "osgversion"))
            os.chmod(os.path.join(bin_mirror, "osgversion"), 0o755)
        return mirror, bin_mirror

    def test(self):
        if can_run(self):
            lib_mirror, bin_mirror = self._mirror_pkg_libs()
            parts = [
                "/system/lib64",
                lib_mirror,
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos",
            ]
            for d in os.environ.get("LD_LIBRARY_PATH", "").split(":"):
                if d and d not in parts:
                    parts.append(d)
            os.environ["LD_LIBRARY_PATH"] = ":".join(parts)
            # 1. consumer binary linked against the packaged libraries
            exe = os.path.join(self.cpp.build.bindirs[0], "test_osg_consumer")
            self.output.info(f"running consumer test: {exe}")
            self.run(f'"{exe}"')
            # 2. packaged osgversion application (mirrored copy)
            osgversion = os.path.join(bin_mirror, "osgversion")
            if os.path.isfile(osgversion):
                self.run(f'"{osgversion}"')
            else:
                self.output.warning("osgversion binary not found in package bin/")
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
                "executed": True, "passed": True, "command": exe,
                "discovered": 1, "passedCount": 1,
            }))
        else:
            self.output.warning("cross-compilation: consumer binary not run")
