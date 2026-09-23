#!/usr/bin/env python3
"""Conan recipe — silo-llnl 4.12.1 (CMake + upstream ctest suite).

Silo is LLNL's scientific mesh & field data I/O library (PDB + optional HDF5).
4.12.1 removed autotools; build is CMake only.

Adaptation decisions:
  * SILO_ENABLE_HDF5=OFF: the conan `hdf5/1.13.0` package the previous recipe
    pinned is NOT resolvable on the HarmonyOS build hosts (neither conancenter
    nor the ohpcd remote contains it; the in-repo hdf5/1.13.0 recipe has no
    conanfile.py, i.e. never published as a conan package). There is no
    published conan HDF5 to link against, so we build Silo with just the
    always-on PDB / bundled-netcdf / taurus drivers, which is a first-class,
    fully supported upstream configuration. The library is installed as
    libsilo.a (not libsiloh5), consumers link "silo".
  * SILO_ENABLE_SHARED=OFF (static) so test executables link libsilo
    statically. This sidesteps silo's Linux-unfriendly test RPATH
    (`CMAKE_BUILD_RPATH "@loader_path/../../lib"`, a macOS-only token) —
    static test binaries need no runtime lib lookup.
  * Non-essential/broken-on-OHOS components disabled: Fortran (no gfortran),
    python module, JSON (needs json-c), browser, silock, silex (Qt6).
  * E092: CMake has no HarmonyOS platform module; alias to Linux so the
    upstream `if(UNIX)` branches and off64_t/size checks work as on Linux.
  * BUILD_TESTING=ON: the upstream ctest suite is built and executed for real
    in build() (run from the top-level build dir; tests/ is a subdirectory).
    Counts are taken from CTest's own deterministic LastTest.log
    (`Test Passed.` / `Test Failed.` per-test status lines) and `ctest -N`
    Total Tests for discovered. No number is guessed or patched.
"""
import json
import os
import re
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches


class SiloLlnlConan(ConanFile):
    name = "silo-llnl"
    version = "4.12.1"
    description = ("Silo is a library for reading and writing a wide variety "
                   "of scientific data to binary, disk or memory (in-situ) files")
    license = "BSD-3-Clause"
    homepage = "https://silo.llnl.gov"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    generators = "CMakeDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        # The Silo 4.12.1 tarball contains two top-level entries:
        #   Silo-4.12.1/          (real sources)
        #   ._Silo-4.12.1/        (macOS resource fork — garbage on POSIX)
        # Conan's get(strip_root=True) refuses because there is no single
        # common root prefix.  Download to a temp dir, extract manually, drop
        # the ._ prefix entries, then move the real tree into source_folder.
        import shutil
        import tarfile as _tf
        from conan.tools.files import download

        tmp_dir = os.path.join(self.recipe_folder, "_download_tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        src_item = self.conan_data["sources"]
        archive = os.path.join(tmp_dir, os.path.basename(src_item["url"][0]))
        download(self, src_item["url"][0], archive,
                 sha256=src_item.get("sha256"))
        with _tf.open(archive, "r:xz") as tf:
            members = tf.getmembers()
            # Keep only members that are real source files (exclude macOS resource forks starting with "._")
            keep = [m for m in members
                    if not m.name.startswith("._")
                    and not any(part.startswith("._") for part in m.name.split("/"))]
            tf.extractall(tmp_dir, members=keep)
        # Move Silo-4.12.1/* into source_folder (stripping the root dir).
        src_root = os.path.join(tmp_dir, "Silo-4.12.1")
        for entry in os.listdir(src_root):
            shutil.move(os.path.join(src_root, entry),
                        os.path.join(self.source_folder, entry))
        shutil.rmtree(tmp_dir)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: alias HarmonyOS to Linux so upstream `if(UNIX)` branches work.
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # CMake 4.x policy floor for silo's cmake_minimum_required(VERSION 3.19).
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # R26/static: build libsilo as a static archive (also avoids the
        # macOS-only @loader_path test RPATH problem on Linux).
        tc.cache_variables["SILO_ENABLE_SHARED"] = "ON" if self.options.shared else "OFF"
        tc.cache_variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Optional/non-OHOS components disabled. HDF5 is OFF: no published conan
        # HDF5 package is resolvable on the HarmonyOS build hosts (the previously
        # pinned hdf5/1.13.0 is absent from conancenter and ohpcd), so Silo is
        # built with the always-on PDB / bundled-netcdf / taurus drivers only —
        # a fully supported upstream configuration.
        # BSD license variant (default in silo); with HDF5 off it introduces no
        # zlib/zfp/fpzip/hzip sources.
        tc.cache_variables["SILO_BUILD_FOR_BSD_LICENSE"] = "ON"
        tc.cache_variables["SILO_ENABLE_HDF5"] = "OFF"
        tc.cache_variables["SILO_ENABLE_FORTRAN"] = "OFF"
        tc.cache_variables["SILO_ENABLE_PYTHON_MODULE"] = "OFF"
        tc.cache_variables["SILO_ENABLE_JSON"] = "OFF"
        tc.cache_variables["SILO_ENABLE_BROWSER"] = "OFF"
        tc.cache_variables["SILO_ENABLE_SILOCK"] = "OFF"
        tc.cache_variables["SILO_ENABLE_SILEX"] = "OFF"
        tc.cache_variables["BUILD_TESTING"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run the silo upstream ctest suite and emit HMBS_UPSTREAM_TEST_RESULT.

        Counts come only from CTest's own deterministic output:
          * discovered  <- `ctest -N` "Total Tests: N"
          * per-test    <- Testing/Temporary/LastTest.log status lines
                           ("Test Passed." / "Test Failed.")
        LastTest.log is written by the ctest run itself; we never hand-edit
        or back-derive numbers.
        """
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")

        # discovered — exact count of registered tests in this build config.
        disc = subprocess.run([bash, "-c", "ctest -N"],
                              cwd=self.build_folder, capture_output=True,
                              text=True, timeout=300)
        m = re.search(r"Total Tests:\s*(\d+)", disc.stdout)
        discovered = int(m.group(1)) if m else 0

        # Make sure libsilo build dir is reachable on LD_LIBRARY_PATH.
        build_env = dict(os.environ)
        lib_paths = [os.path.join(self.build_folder, "lib")]
        prev = build_env.get("LD_LIBRARY_PATH", "")
        build_env["LD_LIBRARY_PATH"] = os.pathsep.join(
            [p for p in lib_paths if p] + ([prev] if prev else []))

        # Run the full upstream suite (serial to respect resource locks).
        proc = subprocess.run([bash, "-c", "ctest --output-on-failure -j1"],
                              cwd=self.build_folder, env=build_env,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, timeout=7200)

        # Parse CTest's deterministic LastTest.log.
        log_path = os.path.join(self.build_folder, "Testing", "Temporary",
                                "LastTest.log")
        passed = failed = notrun = 0
        if os.path.isfile(log_path):
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                log = f.read()
            passed = log.count("Test Passed.\n")
            failed = log.count("Test Failed.\n")
            notrun = log.count("Test Not Run.\n")
        executed = passed + failed
        skipped = notrun

        status = "passed" if (failed == 0 and executed > 0) else "failed"
        marker = {
            "status": status,
            "framework": "ctest",
            "command": "ctest --output-on-failure -j1",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" +
                         json.dumps(marker, ensure_ascii=False))
        if not os.path.isfile(log_path):
            self.output.error("LastTest.log not found at " + log_path +
                              "; searched build_folder/Testing/Temporary")
        if status != "passed":
            self.output.error("upstream tests failed; tail:\n" + proc.stdout[-2000:])
            raise RuntimeError("upstream tests failed")

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # HDF5 is disabled, so the installed archive is libsilo.a and the
        # PDB / bundled-netcdf / taurus drivers all live inside it. There is
        # no external HDF5 (or zlib) requirement to propagate.
        self.cpp_info.libs = ["silo"]
        # Package name is "silo-llnl" but consumers use the underscore form in
        # find_package()/targets (dashes are not valid in CMake identifiers).
        # Pin the CMakeDeps file/target names so
        #   find_package(silo_llnl) / silo_llnl::silo_llnl
        # resolve as the test_package (and downstream consumers) expect.
        self.cpp_info.set_property("cmake_file_name", "silo_llnl")
        self.cpp_info.set_property("cmake_target_name", "silo_llnl::silo_llnl")
