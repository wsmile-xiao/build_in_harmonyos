#!/usr/bin/env python3
"""Conan test_package for slang — functional test via slangc binary and C API (R34).

Tests the slang compiler by:
1. Compiling and running test.cpp (C API link test via CMake)
2. Running slangc --version (smoke test)
3. Compiling a simple shader to SPIR-V
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout, CMakeDeps, CMakeToolchain


class SlangTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Get slangc binary path from the package
        slang_bin = None
        for bindir in self.dependencies["slang"].cpp_info.bindirs:
            candidate = os.path.join(bindir, "slangc")
            if os.path.exists(candidate):
                slang_bin = candidate
                break

        if not slang_bin:
            raise AssertionError("slangc binary not found in package")

        # slangc uses dlopen() to load runtime .so modules (slang-glslang,
        # slang-glsl-module) from its own directory. Set LD_LIBRARY_PATH
        # so the dynamic linker can find them.
        slang_bin_dir = os.path.dirname(slang_bin)
        old_ld = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = slang_bin_dir + (":" + old_ld if old_ld else "")

        # Test 1: Run slangc -h (L2 smoke test — slangc doesn't support --version)
        self.output.info("Running slangc -h (smoke test)...")
        exit_code = self.run(f'"{slang_bin}" -h', env="conanrun")
        if exit_code != 0:
            raise AssertionError(f"slangc -h failed (exit code: {exit_code})")

        # Test 2: Compile a simple HLSL shader
        # Write temp files to build_folder (source_folder may be read-only in Conan cache)
        shader_file = os.path.join(self.build_folder, "test_shader.slang")
        with open(shader_file, "w") as f:
            f.write("""RWStructuredBuffer<float> outputBuffer;
[shader("compute")]
[numthreads(1, 1, 1)]
void computeMain(uint3 id : SV_DispatchThreadID) {
    outputBuffer[id.x] = float(id.x);
}
""")
        output_file = os.path.join(self.build_folder, "test_output.spirv")
        self.output.info("Compiling test shader...")
        exit_code = self.run(f'"{slang_bin}" "{shader_file}" -o "{output_file}" -target spirv',
                             env="conanrun")
        if exit_code != 0:
            raise AssertionError(f"Shader compilation failed (exit code: {exit_code})")

        if os.path.exists(output_file):
            self.output.info("PASS: Shader compiled to SPIR-V successfully")
        else:
            raise AssertionError("FAIL: SPIR-V output file not created")

        # Test 3: Run the C API test binary (compiled in build())
        self.output.info("Running slang C API test...")
        test_bin = os.path.join(self.build_folder, "test_slang")
        if os.path.exists(test_bin):
            exit_code = self.run(f'"{test_bin}"', env="conanrun")
            if exit_code != 0:
                raise AssertionError(f"C API test failed (exit code: {exit_code})")
            self.output.info("PASS: C API test passed")
        else:
            raise AssertionError("C API test binary not found — build() may have failed silently")
