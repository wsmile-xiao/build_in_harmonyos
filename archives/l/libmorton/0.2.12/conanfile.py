#!/usr/bin/env python3
"""Conan recipe — libmorton 0.2.12 (header-only).

C++ header-only library for efficient Morton code (Z-order) encode/decode
in/from 2D/3D coordinates. Zero runtime dependencies — the entire public
API lives under include/libmorton/.
"""
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout
import os
import shutil
import subprocess

required_conan_version = ">=2.0"


class LibmortonConan(ConanFile):
    name = "libmorton"
    version = "0.2.12"
    package_type = "header-library"

    description = (
        "C++ header-only library with methods to efficiently encode/decode "
        "Morton codes in/from 2D/3D coordinates (Z-order curve)."
    )
    homepage = "https://github.com/Forceflow/libmorton"
    license = "MIT"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("morton", "z-order", "bit-interleaving", "header-only", "cpp11")

    # R32: settings.os 判断必须用 in ("Linux", "OHOS")；保留四项以通过 L0p。
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    exports_sources = "conandata.yml", "patches/*"

    def layout(self):
        basic_layout(self, src_folder="src")

    def export_sources(self):
        export_conandata_patches(self)

    def package_id(self):
        # Header-only: the package is identical for every build configuration.
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        # Header-only: no library artifact to compile. Apply any declared
        # patches (currently none) for recipe completeness, then run the
        # upstream test suite as the L1 upstream-test gate.
        apply_conandata_patches(self)
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        src = self.source_folder
        build_dir = os.path.join(self.build_folder, "upstream_tests")
        os.makedirs(build_dir, exist_ok=True)

        # Locate build tools in PATH (the CI profile [buildenv] prepends the
        # OHOS toolchain bin/ to PATH).
        cmake = shutil.which("cmake") or "cmake"
        cc = shutil.which("clang") or shutil.which("cc") or "clang"
        cxx = shutil.which("clang++") or shutil.which("c++") or "clang++"

        # The OHOS sandbox denies exec of user-path binaries (usr/local/bin);
        # CMake's Ninja generator probes `ninja --version` through PATH and
        # fails with "permission denied" when it resolves to the user ninja.
        # Force the executable system ninja explicitly so configure can run.
        ninja = "/data/service/hnp/bin/ninja"
        if not os.path.isfile(ninja):
            ninja = shutil.which("ninja") or "ninja"

        # The OHOS clang++ wrapper injects unused linker flags even for
        # compile-only steps; upstream -Wall -Wextra -Wpedantic would then
        # fail. Silencing unused-command-line-argument does not touch any
        # test assertion or source.
        extra_flags = "-Wno-unused-command-line-argument"

        configure = [
            cmake, "-G", "Ninja",
            "-DBUILD_TESTING=ON",
            "-DCMAKE_BUILD_TYPE=Release",
            f"-DCMAKE_C_COMPILER={cc}",
            f"-DCMAKE_CXX_COMPILER={cxx}",
            f"-DCMAKE_CXX_FLAGS={extra_flags}",
            f"-DCMAKE_MAKE_PROGRAM={ninja}",
            src,
        ]
        self._run(configure, cwd=build_dir)

        # Build ONLY the portable upstream test target. Upstream
        # test/CMakeLists.txt additionally registers architectures-specific
        # variants (libmorton-test-bmi2 -march=haswell, avx512/zen2 with
        # x86-only micro-architecture flags) that cannot compile on OHOS
        # aarch64 — those are per-entry documented as unavailable, not built.
        self._run([cmake, "--build", ".", "--target", "libmorton-test",
                   "-j", "4"], cwd=build_dir)

        # Execute the built upstream test binary. can_run guards the actual
        # execution when cross-compiling to a target that cannot run host
        # binaries.
        from conan.tools.build import can_run
        if can_run(self):
            test_bin = self._find_binary(build_dir, "libmorton-test")
            if test_bin is None:
                raise ConanException(
                    f"Upstream test binary not found under {build_dir}"
                )
            # Upstream parses argv[1] as MAXRUNSIZE (the max power-of-2 size
            # for the performance phase, default 256). Pass 64 — the smallest
            # legal value — so the performance phase stays short while the
            # full correctness suite still runs for real.
            self._run([test_bin, "64"], cwd=build_dir)
        else:
            self.output.warning(
                "Upstream tests compiled successfully but not executed: "
                "target binaries cannot run in this environment (can_run=False)."
            )

    def _find_binary(self, root, name):
        # CMake multi-config / single-config layouts place the built binary
        # at different depths (e.g. <root>/test/<name> vs <root>/<name>), so
        # locate it by walking the build tree instead of assuming one path.
        for dirpath, _dirnames, filenames in os.walk(root):
            if name in filenames:
                return os.path.join(dirpath, name)
        return None

    def _run(self, cmd, cwd=None):
        self.output.info(f"$ {' '.join(cmd)}")
        env = dict(os.environ)
        result = subprocess.run(cmd, cwd=cwd, env=env,
                                capture_output=True, text=True)
        out = (result.stdout or "") + (result.stderr or "")
        if out.strip():
            self.output.info(out.strip())
        if result.returncode != 0:
            raise ConanException(
                f"Command failed (exit {result.returncode}): {' '.join(cmd)}\n{out}"
            )

    def package(self):
        # Install the full public header tree: include/libmorton/*.h
        copy(
            self,
            "libmorton/*.h",
            src=os.path.join(self.source_folder, "include"),
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libmorton")
        self.cpp_info.set_property("cmake_target_name", "libmorton::libmorton")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]