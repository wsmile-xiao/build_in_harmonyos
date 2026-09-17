#!/usr/bin/env python3
"""Conan test_package — libagg 2.5.

Direct compile+run (no CMake/find_package): test.cpp links against the
installed libagg.a/libagg.so and agg2/ headers from the main package.
This avoids relying on Conan's CMakeDeps config-file generation, which
is unreliable on this OHOS Conan build.

Also runs the HarmonyOS-specific binary audit (test_ohos.sh) which
verifies ELF64 AArch64, musl NEEDED entries, SONAME, .codesign and
RPATH of the installed library.
"""
import os

from conan import ConanFile


class LibAggTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # No generators: we compile test.cpp directly with the package's
    # headers and static lib, no CMake config needed.

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Resolve the installed package's include/ and lib/ dirs.
        agg = self.dependencies["libagg"]
        cpp = agg.cpp_info
        inc = cpp.includedirs[0] if cpp.includedirs else "include"
        libdir = cpp.libdirs[0] if cpp.libdirs else "lib"
        shared = getattr(agg.options, "shared", False)
        # Compile and link test.cpp against libagg.
        # (register-keyword & C++11 const issues already fixed by patch 0002)
        # Shared builds: embed an RPATH to the package lib dir so the test
        # binary finds libagg.so.2 without requiring LD_LIBRARY_PATH setup.
        rpath = f" -Wl,-rpath,{os.path.join(agg.package_folder, libdir)}" if shared else ""
        self.run(
            f"clang++ -std=c++17 -O2"
            f" -I{inc}"
            f" test.cpp"
            f" -L{libdir} -lagg{rpath}"
            f" -o test_libagg",
            cwd=self.build_folder,
        )

    def test(self):
        # 1. Consumer-level rendering tests (pixel-buffer verification)
        self.run("./test_libagg", cwd=self.build_folder)
        # 2. HarmonyOS-specific checks on the installed artifacts
        #    (ELF64/AArch64/musl/SONAME/.codesign/RPATH)
        agg = self.dependencies["libagg"]
        cpp = agg.cpp_info
        pkg_libdir = cpp.libdirs[0] if cpp.libdirs else "lib"
        pkg_folder = agg.package_folder
        shared = getattr(agg.options, "shared", False)
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_ohos.sh")
        # run()'s env arg is a list of env-FILE names; must be .sh files
        # containing `export K=V` lines that the wrapper sources first.
        env_file = os.path.join(self.build_folder, "ohos_env.sh")
        with open(env_file, "w") as f:
            f.write(f'export PKG_LIBDIR="{os.path.join(pkg_folder, pkg_libdir)}"\n')
            f.write(f"export SHARED_BUILD={'1' if shared else '0'}\n")
        self.run(f'bash "{script}"', cwd=self.build_folder, env=[env_file])
