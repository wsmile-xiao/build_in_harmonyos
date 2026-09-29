#!/usr/bin/env python3
"""Conan recipe for StormLib 9.40 — MPQ archive library (Blizzard formats).

HarmonyOS (aarch64) adaptation.  StormLib is C++11 built with CMake; the
only external dependencies are zlib and bzip2, both already published in
ohpcd.  libtomcrypt/libtommath are vendored by upstream and compiled in.

CMake notes:
* ``STORM_USE_BUNDLED_LIBRARIES=OFF`` (default) makes CMake's
  ``find_package(ZLIB)`` / ``find_package(BZip2)`` resolve to the Conan
  packages via CMakeDeps, so ``-D__SYS_ZLIB`` / ``-D__SYS_BZLIB`` are
  defined and the vendored copies are skipped.
* ``STORM_BUILD_TESTS=ON``: the upstream CTest entry (StormLib_test) is
  built and *executed* on the device.  ALSA (hard-required by
  test/CMakeLists.txt) comes from the Conan ``alsa-lib`` package via
  ``test_requires``, and ``STORMTEST_USE_OLD_PATHS=OFF`` relocates the
  work root into the build tree.  The suite cannot fully pass anywhere:
  its data set ("1995 - Test MPQs") is the author's private Blizzard
  archive collection, absent from the repo and from every release, and
  upstream CI only builds this target without running it — the real run
  output and its concrete error are recorded in the
  ``HMBS_UPSTREAM_TEST_RESULT`` marker instead of failing the build.
  Functional coverage for the packaged library lives in test_package
  (real MPQ create/write/close/reopen/read round trip).
* Static by default (``BUILD_SHARED_LIBS`` follows the ``shared`` option).
  The library is installed as ``libstorm.a`` / ``libstorm.so`` with public
  headers StormLib.h / StormPort.h.

R26: ``storm`` is not a system library name — no collision; the recipe
still drives BUILD_SHARED_LIBS explicitly so consumers can pick.
R32: settings.os must check in ("Linux", "OHOS").
"""
import json
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class StormLibConan(ConanFile):
    name = "stormlib"
    version = "9.40"
    description = "StormLib is a library for handling MPQ archives (Blizzard games)"
    license = "MIT"
    homepage = "https://github.com/ladislav-zezula/StormLib"
    url = "https://github.com/ladislav-zezula/StormLib"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires("zlib/1.3.1.1")
        self.requires("bzip2/1.0.8.2")

    def build_requirements(self):
        # StormLib_test hard-links ALSA (test/CMakeLists.txt
        # find_package(ALSA REQUIRED)); alsa-lib provides ALSA::ALSA.
        # Only used for the upstream test target — not a consumer dep.
        self.test_requires("alsa-lib/1.2.16")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        # Use the Conan-provided zlib/bzip2 rather than the vendored copies.
        tc.variables["STORM_USE_BUNDLED_LIBRARIES"] = False
        # Build AND run the upstream CTest entry (see module docstring);
        # the run result is recorded, not gated.
        tc.variables["STORM_BUILD_TESTS"] = True
        # Relocate the suite's work root from the OS-hardcoded path into
        # the build tree (its data set is private, so the run reports the
        # concrete initialization error and exits non-zero).
        tc.variables["STORMTEST_USE_OLD_PATHS"] = False
        # Vendored libtomcrypt/libtommath (the Linux default).
        tc.variables["WITH_LIBTOMCRYPT"] = False
        tc.generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def _upstream_ld_library_path(self):
        # The freshly built aarch64 StormLib_test is executed in-place; any
        # shared dependency (alsa-lib → libasound) must be locatable.  Walk
        # the whole dependency graph — hardcoded names silently miss
        # transitive libs (leapp-cli lesson).
        paths = []
        for dep in self.dependencies.values():
            for d in dep.cpp_info.libdirs:
                if d and d not in paths:
                    paths.append(d)
        return paths

    def _run_upstream_tests(self):
        """Execute the upstream CTest entry (StormLib_test) for real.

        The suite's data set ("1995 - Test MPQs") is the author's private
        Blizzard archive collection: absent from the git repo and from every
        GitHub release, and upstream CI (build.yml) only *builds* this
        target, never runs it.  The run below is therefore real on the
        device, but cannot fully pass anywhere; its outcome — including the
        concrete error — is recorded in the HMBS_UPSTREAM_TEST_RESULT
        marker without failing the build.  Functional coverage of the
        packaged library itself lives in test_package (real MPQ round trip).
        """
        exe = os.path.join(self.build_folder, "test", "StormLib_test")
        marker = {"status": "failed", "framework": "ctest",
                  "command": "./test/StormLib_test",
                  "discovered": 1, "executed": 0,
                  "passed": 0, "failed": 0, "skipped": 0}
        if not os.path.isfile(exe):
            marker["reason"] = "StormLib_test binary not produced"
        else:
            env = dict(os.environ)
            ld = self._upstream_ld_library_path()
            if ld:
                env["LD_LIBRARY_PATH"] = ":".join(
                    ld + [env.get("LD_LIBRARY_PATH", "")]).rstrip(":")
            try:
                proc = subprocess.run([exe], cwd=self.build_folder, env=env,
                                      capture_output=True, text=True,
                                      timeout=300)
                marker["executed"] = 1
                tail = [ln for ln in
                        ((proc.stdout or "") + (proc.stderr or "")).splitlines()
                        if ln.strip()][-6:]
                if proc.returncode == 0:
                    marker["status"] = "passed"
                    marker["passed"] = 1
                else:
                    marker["failed"] = 1
                    marker["reason"] = "exit=%d" % proc.returncode
                self.output.info("=== StormLib_test tail ===\n" +
                                 "\n".join(tail))
            except subprocess.TimeoutExpired:
                marker["executed"] = 1
                marker["failed"] = 1
                marker["reason"] = "timeout after 300s"
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" +
                         json.dumps(marker, ensure_ascii=False))

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # STORM_BUILD_TESTS=ON also installs the StormLib_test binary; the
        # package ships the library only.
        test_bin = os.path.join(self.package_folder, "bin", "StormLib_test")
        if os.path.isfile(test_bin):
            os.remove(test_bin)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "StormLib")
        self.cpp_info.set_property("cmake_target_name", "StormLib::storm")
        self.cpp_info.libs = ["storm"]
        self.cpp_info.includedirs = ["include"]
        # StormLib's public headers pull in zlib/bzip2 types when the
        # system-library defines are active.
        self.cpp_info.requires = ["zlib::zlib", "bzip2::bzip2"]
