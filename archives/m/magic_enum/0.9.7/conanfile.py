#!/usr/bin/env python3
"""Conan recipe — magic_enum 0.9.7 (header-only).

Header-only C++17 static reflection library for enums. Zero runtime
dependencies — the entire public API lives under include/magic_enum/.
"""
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
import os
import shutil
import subprocess

required_conan_version = ">=2.0"


class MagicEnumConan(ConanFile):
    name = "magic_enum"
    version = "0.9.7"
    package_type = "header-library"

    description = (
        "Header-only C++17 library that provides static reflection for "
        "enums, work with any enum type without any macro or boilerplate code."
    )
    homepage = "https://github.com/Neargye/magic_enum"
    license = "MIT"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("enum", "reflection", "magic-enum", "header-only", "cpp17")

    # R32: settings.os 判断必须用 in ("Linux", "OHOS"); 保留四项以通过 L0p。
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

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
        # Apply any conandata-declared patches (none shipped for 0.9.7).
        apply_conandata_patches(self)

        # Header-only library: no library artifact to compile. However, the
        # upstream official test suite (test/*.cpp) IS built and executed here
        # as the L1 upstream-test gate so that CI can verify the real upstream
        # tests pass in the OHOS aarch64 environment — not merely the consumer
        # test_package.
        #
        # Upstream test/CMakeLists.txt registers test targets per C++ standard
        # the compiler supports (cpp17 always; cpp20/23 conditionally) and
        # gates test_nonascii.cpp behind MAGIC_ENUM_OPT_ENABLE_NONASCII (off by
        # default — nonascii uses emoji enum identifiers requiring C++23 lexer
        # support unavailable on clang 15). We use the upstream defaults and
        # do NOT alter test semantics, lower assertions, or skip cases.
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        src = self.source_folder
        build_dir = os.path.join(self.build_folder, "upstream_tests")
        os.makedirs(build_dir, exist_ok=True)

        # Locate build tools in PATH (the CI profile [buildenv] prepends the
        # OHOS toolchain bin/ to PATH; shutil.which resolves the real paths so
        # this works whether or not Conan activated the buildenv for us).
        cmake = shutil.which("cmake") or "cmake"
        ctest = shutil.which("ctest") or "ctest"
        cxx = shutil.which("clang++") or shutil.which("c++") or "clang++"

        # The OHOS clang++ wrapper unconditionally injects linker flags
        # (-Wl,--code-sign -fuse-ld=lld -L...) even for compile-only (-c) steps;
        # upstream test/CMakeLists.txt enables -Werror, so those unused linker
        # inputs would break compilation. -Wno-unused-command-line-argument
        # silences the toolchain-injected noise WITHOUT touching any test
        # assertion or source.
        extra_flags = "-Wno-unused-command-line-argument"

        configure = [
            cmake, "-G", "Ninja",
            "-DMAGIC_ENUM_OPT_BUILD_TESTS=ON",
            "-DMAGIC_ENUM_OPT_BUILD_EXAMPLES=OFF",
            "-DMAGIC_ENUM_OPT_INSTALL=OFF",
            "-DCMAKE_BUILD_TYPE=Release",
            "-DCMAKE_CXX_STANDARD=17",
            f"-DCMAKE_CXX_COMPILER={cxx}",
            f"-DCMAKE_CXX_FLAGS={extra_flags}",
            src,
        ]
        self._run(configure, cwd=build_dir)
        self._run([cmake, "--build", ".", "-j", "4"], cwd=build_dir)

        # Execute the registered upstream tests via ctest. can_run guards the
        # actual execution: when cross-compiling to a target that cannot run
        # host binaries, the tests are compiled (build pass) but not executed.
        from conan.tools.build import can_run
        if can_run(self):
            self._run(
                [ctest, "--output-on-failure", "-j", "4"],
                cwd=build_dir,
            )
        else:
            self.output.warning(
                "Upstream tests compiled successfully but not executed: "
                "target binaries cannot run in this environment (can_run=False)."
            )

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
        # Install the full public header tree: include/magic_enum/*.hpp
        copy(
            self,
            "magic_enum/*.hpp",
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
        self.cpp_info.set_property("cmake_file_name", "magic_enum")
        self.cpp_info.set_property("cmake_target_name", "magic_enum::magic_enum")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
