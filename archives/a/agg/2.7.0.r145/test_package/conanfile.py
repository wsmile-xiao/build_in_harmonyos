#!/usr/bin/env python3
"""Conan test_package — agg 2.7.0.r145.

Direct compile+run (no CMake/find_package): test.cpp links against the
installed libagg.a and agg2/ headers from the main package. This avoids
relying on Conan's CMakeDeps config-file generation, which is unreliable
on this OHOS Conan build.
"""
from conan import ConanFile


class AggTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # No generators: we compile test.cpp directly with the package's
    # headers and static lib, no CMake config needed.

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Resolve the installed package's include/ and lib/ dirs.
        agg = self.dependencies["agg"]
        cpp = agg.cpp_info
        inc = cpp.includedirs[0] if cpp.includedirs else "include"
        libdir = cpp.libdirs[0] if cpp.libdirs else "lib"
        # Compile and link test.cpp against libagg.a.
        # C++17 (agg is template-only), static lib, no system deps.
        self.run(
            f"clang++ -std=c++17 -O2"
            f" -I{inc}"
            f" test.cpp"
            f" -L{libdir} -lagg"
            f" -o test_agg",
            cwd=self.build_folder,
        )

    def test(self):
        # Run the compiled binary; non-zero exit fails the test.
        self.run("./test_agg", cwd=self.build_folder)
