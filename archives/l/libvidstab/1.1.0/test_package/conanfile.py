#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_package — libvidstab 1.1.0 consumer test (links real libvidstab, exercises core vid.stab APIs)."""
#
# This test_package links against the real libvidstab and calls core
# vid.stab APIs (VSFrameInfo, VSMotionDetectConfig, VSTransform,
# VSTransformations lifecycle + addTransforms).  It does NOT depend on
# FFmpeg — those calls are the pure-C core that libvidstab ships.

import os
import shutil
import subprocess
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class TestVidstabConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    # CMakeToolchain is instantiated explicitly in generate() (not listed
    # here) so we can repair the compiler conf before it writes
    # conan_toolchain.cmake.  Listing it in `generators` would make Conan run
    # it BEFORE generate(), baking in the (stale) profile compiler path.
    generators = "CMakeDeps", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # Repair the (possibly stale) compiler paths from the shared OHOS
        # profile BEFORE generating the CMake toolchain.  The profile pins
        # tools.build:compiler_executables to /data/service/hnp/bin/clang,
        # which does NOT exist on native HarmonyOS-PC developer machines (the
        # real aarch64-unknown-linux-ohos clang is on PATH via buildenv).  Left
        # unrepaired, CMakeToolchain writes that non-existent path into
        # conan_toolchain.cmake and cmake.configure() dies at project() with
        # "is not a full path to an existing compiler tool".  The override is a
        # no-op where the profile path IS valid.  (Same logic as the recipe's
        # generate(); duplicated here because test_package is a separate
        # conanfile that generates its own toolchain.)
        comp = self.conf.get("tools.build:compiler_executables", default={},
                             check_type=dict) or {}

        def _resolve(conf_path, basename):
            if conf_path and os.path.exists(conf_path):
                return conf_path
            found = shutil.which(basename)
            if found and os.path.exists(found):
                self.output.info(
                    f"[test_vidstab] profile compiler "
                    f"'{conf_path or basename}' not found; using '{found}' "
                    f"from PATH")
                return found
            return conf_path

        new_comp = dict(comp)
        new_comp["c"] = _resolve(comp.get("c"), "clang")
        new_comp["cpp"] = _resolve(comp.get("cpp"), "clang++")
        self.conf.define("tools.build:compiler_executables", new_comp)

        # Now generate the toolchain with the repaired conf.
        tc = CMakeToolchain(self)
        tc.generate()

    # ------------------------------------------------------------------ #
    # OHOS SDK linker runtime path (CI libxml2.so.16 regression fix)
    # ------------------------------------------------------------------ #
    # test_package re-implements the same SDK-lib derivation + branched
    # linker probe + Environment() prepend as the recipe (see
    # archives/l/libvidstab/1.1.0/conanfile.py for the full root-cause
    # note).  In short: CMake's try_compile in the consumer configure()
    # step links via the OHOS SDK lld, which needs libxml2.so.16 on
    # LD_LIBRARY_PATH; on CI-040 the ambient path is wrong and lld fails
    # to start with "The C compiler is not able to compile a simple test
    # program".  We derive the SDK llvm/lib from realpath(CC) +
    # clang -print-resource-dir, confirm libxml2.so.16, probe the linker,
    # and prepend the lib dir for configure/build/run.  No SDK version,
    # currentUser, or absolute path is hard-coded.
    def _sdk_llvm_libdir(self):
        """Locate the OHOS SDK llvm/lib dir that holds libxml2.so.16."""
        if str(self.settings.os) != "OHOS":
            return ""

        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c") or compilers.get("cpp")
        candidates = []
        if cc:
            compiler = os.path.realpath(cc)
            try:
                resource_dir = subprocess.check_output(
                    [cc, "-print-resource-dir"],
                    stderr=subprocess.DEVNULL, text=True,
                ).strip()
                if resource_dir:
                    # resource_dir = <sdk>/lib/clang/<ver>  ->  <sdk>/lib
                    candidates.append(os.path.dirname(os.path.dirname(resource_dir)))
            except (OSError, subprocess.CalledProcessError):
                pass
            candidates.append(os.path.join(os.path.dirname(os.path.dirname(compiler)), "lib"))

        for candidate in dict.fromkeys(candidates):
            if os.path.isfile(os.path.join(candidate, "libxml2.so.16")):
                return candidate
        return ""

    def _usable_sdk_llvm_libdir(self):
        """Return the SDK llvm/lib dir after proving its linker can start.

        Probes the OHOS SDK linker with the lib dir prepended so the probe
        itself exercises the same libxml2.so.16 resolution that CMake's
        try_compile will need.  The probe is branched on which driver entry
        point the SDK ships:
          - ld.lld  (GNU-flavor symlink) -> `ld.lld --version`
          - lld     (generic driver)     -> `lld -flavor gnu --version`
        NOTE: `ld.lld -flavor gnu --version` is WRONG — ld.lld is already
        GNU-flavored and does not accept -flavor; only the generic `lld`
        driver does.  Do not blend the two.
        Raises ConanException if the linker is missing or its probe fails.
        """
        if str(self.settings.os) != "OHOS":
            return ""

        cached = getattr(self, "_checked_sdk_llvm_libdir", None)
        if cached is not None:
            return cached

        sdk_llvm_lib = self._sdk_llvm_libdir()
        if not sdk_llvm_lib:
            raise ConanException(
                "Cannot locate the active OHOS SDK llvm/lib containing "
                "libxml2.so.16")

        sdk_bin = os.path.join(os.path.dirname(sdk_llvm_lib), "bin")
        ld_lld = os.path.join(sdk_bin, "ld.lld")
        lld = os.path.join(sdk_bin, "lld")
        if os.path.isfile(ld_lld):
            probe_cmd = [ld_lld, "--version"]
        elif os.path.isfile(lld):
            probe_cmd = [lld, "-flavor", "gnu", "--version"]
        else:
            raise ConanException(
                f"Cannot find the OHOS SDK linker (ld.lld/lld) in {sdk_bin}")

        probe_env = os.environ.copy()
        old_ld_path = probe_env.get("LD_LIBRARY_PATH", "")
        probe_env["LD_LIBRARY_PATH"] = os.pathsep.join(
            part for part in (sdk_llvm_lib, old_ld_path) if part)
        try:
            probe = subprocess.run(
                probe_cmd, env=probe_env,
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                text=True, timeout=10, check=False)
        except (OSError, subprocess.SubprocessError) as error:
            raise ConanException(
                f"Cannot execute the active OHOS SDK linker "
                f"{' '.join(probe_cmd)}: {error}") from error
        if probe is not None and probe.returncode == 0:
            self._checked_sdk_llvm_libdir = sdk_llvm_lib
            return sdk_llvm_lib
        raise ConanException(
            f"The active OHOS SDK linker failed its probe: "
            f"{' '.join(probe_cmd)}; stderr={probe.stderr.strip()!r}")

    def _build_environment(self):
        """Build env with the SDK linker runtime path prepended.

        Covers the test_package cmake.configure() (incl. CMake try_compile),
        cmake.build(), and the test() run of the consumer binary.
        """
        environment = Environment()
        sdk_llvm_lib = self._usable_sdk_llvm_libdir()
        if sdk_llvm_lib:
            self.output.info(
                f"[test_vidstab] prepending OHOS SDK linker runtime path: "
                f"{sdk_llvm_lib}")
            environment.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        return environment

    def build(self):
        cmake = CMake(self)
        # The SDK linker runtime path (libxml2.so.16 resolution) MUST wrap
        # CMake's try_compile link stage too — configure() probes the
        # compiler before any test_vidstab source is built, and on CI-040
        # that probe is exactly where lld fails to load libxml2.so.16.
        with self._build_environment().vars(self).apply():
            cmake.configure()
            cmake.build()

    def test(self):
        # This machine IS native HarmonyOS aarch64 (uname -m=aarch64, HarmonyOS
        # HongMeng Kernel, /lib/ld-musl-aarch64.so.1).  The Conan cross_building()
        # heuristic returns True (build host "Linux" != target "OHOS") and thus
        # can_run() returns False— but on an actual OHOS PC the aarch64 ELF runs
        # natively.  We override that incorrect skip and always run the binary,
        # because we've verified the dynamic loader + libc exist on this host.
        exe = os.path.join(self.cpp.build.bindir, "test_vidstab")
        with self._build_environment().vars(self).apply():
            self.run(exe, env="conanrun")
