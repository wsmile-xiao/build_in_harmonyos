# test_package/conanfile.py — libhpptools 1.1.1
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Test-only: the unmodified upstream Catch suite (examples/test-alg.cpp)
        # includes <boost/preprocessor.hpp> for stringize/counter macros.
        # Never propagated to consumers of libhpptools.
        self.requires("boost/1.91.0.1.3")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        # OHOS environment quirk (same verified workaround as the in-repo
        # zmusic 1.3.0 recipe): when the conan client's own stdout is a pipe
        # (as under conan-verify's capture_output), make driven through the
        # CMake helper fails with a bare "Error 1" and zero compiler
        # diagnostics, while the identical command succeeds when run
        # directly. Bypass the helper with subprocess.run and retry.
        import os
        import subprocess
        import time

        from conan.errors import ConanException

        build_retries = 3
        cmd = f'cmake --build "{self.build_folder}"'
        for attempt in range(1, build_retries + 1):
            proc = subprocess.run(cmd, shell=True, capture_output=True,
                                  text=True, cwd=self.build_folder,
                                  env=os.environ)
            if proc.returncode == 0:
                if proc.stdout:
                    self.output.info(proc.stdout[-2000:])
                break
            tail = (proc.stdout or "") + (proc.stderr or "")
            self.output.warning(
                f"test_package build attempt {attempt}/{build_retries} "
                f"failed (rc={proc.returncode}), output tail:\n{tail[-2000:]}"
            )
            if attempt == build_retries:
                raise ConanException(
                    f"test_package build failed {build_retries} times, "
                    f"output tail:\n{tail[-4000:]}"
                )
            time.sleep(5)

    def test(self):
        # Two consumer binaries are built against the packaged headers:
        # - test_consumer: OHOS consumer smoke test covering the headers the
        #   upstream suite does not exercise (zstr/tpool/pfor/logger/
        #   logsum/logsumset/logdiff/strict_fstream). Its return code is the
        #   canonical PASS/FAIL signal.
        # - test_alg: the unmodified upstream Catch suite (9 test cases,
        #   bundled catch.hpp), executed for real per R51.
        import os

        for bin_name in ("test_consumer", "test_alg"):
            # cmake_layout puts binaries under build/<Release|RelWithDebInfo>/
            # or build/ depending on the generator setup; probe both.
            bin_path = os.path.join(self.build_folder, bin_name)
            if not os.path.exists(bin_path):
                bin_path = os.path.join(
                    self.build_folder, "Release", bin_name
                )
            self.run(f'"{bin_path}"', cwd=self.build_folder, env="conanrun")
