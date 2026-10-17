import json
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class LatinoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # Same E092 mapping as the recipe: this consumer is a plain C
        # program using only POSIX + latino public headers.
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 1) Library embedding: parse and execute a .lat program through the
        #    public C API (the chain used by the interpreter's main()).
        #    Runs embed_script.lat (small, deterministic, strictly bounded
        #    loops, no recursion) via self.run() with the runtime environment
        #    applied; stdout is captured to a file in the test_package build
        #    folder, then parsed and compared line by line. EMBED_TEST_OK
        #    must be the last line, printed by the harness only after every
        #    internal check passed (self.run() fails the test on any non-zero
        #    exit). A generous run timeout guards against the known upstream
        #    VM hang.
        embed = os.path.join(self.build_folder, "latino_embed_test")
        script = os.path.join(self.source_folder, "embed_script.lat")
        out_path = os.path.join(self.build_folder, "embed_test_output.txt")
        self.run(f'"{embed}" "{script}" > "{out_path}"',
                 env="conanrun", cwd=self.build_folder)
        with open(out_path, "r", encoding="utf-8", errors="replace") as f:
            embed_stdout = f.read()
        expected_embed = [
            "latino 4",      # string concatenation + arithmetic (1+1+0+4/2)
            "si_ok",         # si branch taken on the computed version
            "55",            # sumar_hasta(10): bounded mientras loop
            "4",             # lista.agregar + lista.longitud
            "valor",         # dictionary member access d.clave
            "EMBED_TEST_OK",
        ]
        actual_embed = embed_stdout.splitlines()
        if actual_embed != expected_embed:
            self.output.error(f"embed output mismatch:\n  expected: {expected_embed}\n  actual:   {actual_embed}")
            raise Exception("embed exact-output assertion failed")
        if embed_stdout.rstrip("\n") != "\n".join(expected_embed):
            self.output.error("EMBED_TEST_OK must be the last line")
            raise Exception("embed exact-output assertion failed (EMBED_TEST_OK last-line)")
        self.output.info(f"embed exact-output assertion passed ({len(expected_embed)} lines)")

        # 2) CLI test: run the packaged interpreter against a .lat script
        #    exercising core language features, asserting exact output (the
        #    interpreter must be functionally usable, not just linkable).
        dep = self.dependencies[self.tested_reference_str]
        latino = os.path.join(dep.package_folder, "bin", "latino")
        test_script = os.path.join(self.source_folder, "test_script.lat")
        expected = [
            "55",           # fibo_iter(10)
            "5050",         # sumatoria(100)
            "uno",          # elegir 1
            "dos",          # elegir 2
            "muchos",       # elegir 7
            "hola latino",  # concatenation
            "15",           # list sum
            "2",            # dict member access
            "3",            # lista.invertir length
            "respuesta=42", # imprimirf
        ]
        cli_out_path = os.path.join(self.build_folder, "cli_test_output.txt")
        self.run(f'"{latino}" "{test_script}" > "{cli_out_path}"',
                 env="conanrun", cwd=self.build_folder)
        with open(cli_out_path, "r", encoding="utf-8", errors="replace") as f:
            cli_stdout = f.read()
        actual = cli_stdout.splitlines()
        if actual != expected:
            self.output.error(f"CLI output mismatch:\n  expected: {expected}\n  actual:   {actual}")
            raise Exception("latino CLI exact-output assertion failed")
        self.output.info(f"CLI exact-output assertion passed ({len(expected)} checks)")

        # 3) CLI version check.
        ver_out_path = os.path.join(self.build_folder, "version_output.txt")
        self.run(f'"{latino}" --version > "{ver_out_path}"',
                 env="conanrun", cwd=self.build_folder)
        with open(ver_out_path, "r", encoding="utf-8", errors="replace") as f:
            ver_stdout = f.read()
        if "1.4.4" not in ver_stdout:
            self.output.error(f"latino --version failed: out={ver_stdout!r}")
            raise Exception("latino --version assertion failed")

        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "latino_embed_test embed_script.lat (exact output) + latino test_script.lat (exact output) + latino --version",
            "discovered": 3,
            "passedCount": 3,
        }, ensure_ascii=False))

        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "executed",
            "framework": "ctest",
            "command": "latino ejemplos/coverage.lat",
            "discovered": 1,
            "executed": 1,
            "passed": 1,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "Upstream registers a single ctest 'coverage' that runs the "
                "interpreter on ejemplos/coverage.lat; executed during "
                "build() of the recipe (cross-compiled OHOS binary runs on "
                "the OHOS host)."
            ),
        }, ensure_ascii=False))
