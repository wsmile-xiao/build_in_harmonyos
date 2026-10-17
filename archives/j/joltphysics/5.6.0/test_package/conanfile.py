#!/usr/bin/env python3
"""test_package for joltphysics 5.6.0 — upstream HelloWorld-derived smoke test.

Builds test_package.cpp (a real physics simulation: dynamic sphere falls onto
a static floor box, simulated until sleep, final rest height asserted) against
the installed libJolt.a and runs it when the target allows execution.

OHOS specifics (boost/1.85.0 precedent):
  - compile uses the OHOS clang++ from the conanbuild env
  - run action locates the SDK libc++_shared.so via
    `clang++ -print-file-name=libc++_shared.so` self-introspection and
    prepends it to LD_LIBRARY_PATH (not in default loader search path)
  - dependency libdir closure appended to LD_LIBRARY_PATH
"""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class JoltPhysicsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["joltphysics"].cpp_info
        libdir = dep.libdirs[0]
        inc = " ".join(["-I" + p for p in dep.includedirs])
        cc = os.environ.get("CXX", "clang++")
        link = " ".join(["-L" + p for p in dep.libdirs] + ["-l" + l for l in dep.libs])
        # Static libJolt.a needs pthread; assert the archive exists.
        so = os.path.join(libdir, "libJolt.a")
        assert os.path.isfile(so), f"libJolt.a not found: {so}"
        # -std=c++17: Jolt headers require C++17 (is_trivially_constructible_v)
        # -DNDEBUG: matches the Release-built libJolt.a — without it Core.h
        # enables JPH_DEBUG -> JPH_ENABLE_ASSERTS -> references
        # JPH::AssertFailed which only exists in assert-enabled builds.
        # -D<defines>: ABI-mandatory PUBLIC defines from package_info
        # (JPH_VERSION_FEATURES runtime check aborts on mismatch).
        defines = " ".join(["-D" + d for d in dep.defines])
        self.run(f"{cc} -std=c++17 -DNDEBUG {defines} {inc} test_package.cpp -o test_jolt {link} -lpthread")

    def test(self):
        # ELF magic verification always runs (binary was produced)
        bin_path = os.path.join(self.build_folder, "test_jolt")
        assert os.path.isfile(bin_path), f"test_jolt not found: {bin_path}"
        with open(bin_path, "rb") as f:
            magic = f.read(4)
        assert magic == b"\x7fELF", f"test_jolt is not an ELF binary: {magic!r}"
        self.output.info(f"test_jolt built and has ELF magic: {bin_path}")

        if not can_run(self):
            self.output.info("cross-building: compile+link verification only")
            return

        # Real physics simulation: sphere falls, collides, rests, sleeps.
        # Exit code 0 = PASS (rest height asserted inside the binary).
        #
        # Runtime env: OHOS clang links test executables against the SDK
        # libc++_shared.so which is not in the default loader search path.
        cxx = os.environ.get("CXX", "clang++")
        run_env = {}
        try:
            probe = subprocess.run([cxx, "-print-file-name=libc++_shared.so"],
                                   capture_output=True, text=True, timeout=30)
            libcxx_file = probe.stdout.strip()
            if probe.returncode == 0 and libcxx_file.startswith("/"):
                libcxx_dir = os.path.dirname(libcxx_file)
                if os.path.isdir(libcxx_dir):
                    run_env["LD_LIBRARY_PATH"] = (
                        libcxx_dir + os.pathsep
                        + os.environ.get("LD_LIBRARY_PATH", ""))
                    self.output.info(f"libc++_shared.so dir: {libcxx_dir}")
        except (subprocess.TimeoutExpired, OSError) as e:
            self.output.warning(f"libc++ probe failed: {e}")

        # Dependency libdir closure appended to LD_LIBRARY_PATH (recursive
        # deps pattern; for self-contained joltphysics this is a no-op but
        # keeps the repo-standard conanrun composition).
        dep_libdirs = []
        for _ref, _d in self.dependencies.items():
            dep_libdirs += _d.cpp_info.libdirs
        if dep_libdirs:
            run_env["LD_LIBRARY_PATH"] = (
                run_env.get("LD_LIBRARY_PATH", "")
                + os.pathsep + os.pathsep.join(dep_libdirs))

        # Run via subprocess with the composed env (barrier/2.4.0 precedent):
        # conanrun for a self-contained static package is empty, and OHOS
        # conan run() env only accepts generator-file lists, so the
        # LD_LIBRARY_PATH composition is passed to Popen directly.
        run_env_full = os.environ.copy()
        for k, v in run_env.items():
            run_env_full[k] = v
        proc = subprocess.run(["./test_jolt"], cwd=self.build_folder,
                              env=run_env_full, capture_output=True,
                              text=True, timeout=600)
        out = (proc.stdout or "") + (proc.stderr or "")
        print(out, end="", flush=True)
        if proc.returncode != 0:
            raise ConanException(
                f"test_jolt failed with exit code {proc.returncode}")
        self.output.info("test_jolt PASSED")
