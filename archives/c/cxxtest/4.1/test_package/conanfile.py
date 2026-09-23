#!/usr/bin/env python3
"""Conan consumer test for cxxtest 4.1 — drives the packaged artifacts the
way a downstream project does:
1. run the packaged cxxtestgen (Python 3 driver from res/) to generate the
   test runner source from the suite header;
2. compile the generated runner with the consumer toolchain (CMake, via the
   CxxTest::CxxTest interface target);
3. execute the signed binary (E077) and assert the ErrorPrinter runner
   reports a successful run ("OK!")."""
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CxxTestTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # Step 1: use the packaged cxxtestgen driver to create the runner.
        # This exercises the Python package installed under res/ (R34: the
        # test genuinely depends on the package artifacts — headers alone
        # cannot produce a runnable runner without the generator).
        # The driver has no __main__ guard, so it is invoked via a tiny
        # inline shim that imports the package and calls main() explicitly.
        dep = self.dependencies["cxxtest"]
        res_dir = os.path.join(dep.package_folder, dep.cpp_info.resdirs[0])
        src_dir = os.path.dirname(os.path.abspath(__file__))
        out = os.path.join(self.build_folder, "generated_runner.cpp")
        suite = os.path.join(src_dir, "test_cxxtest.h")
        env = dict(os.environ)
        env["PYTHONPATH"] = res_dir + os.pathsep + env.get("PYTHONPATH", "")
        shim = (
            "import sys; "
            "sys.argv = ['cxxtestgen', '--error-printer', '-o', "
            f"{out!r}, {suite!r}]; "
            "from cxxtest import cxxtestgen; "
            "cxxtestgen.main(sys.argv)"
        )
        # R33 spirit: never rely on a bare "python3" from PATH — CI workers
        # run conan with a stripped environment where python3 is absent from
        # the subprocess search path. sys.executable is the interpreter that
        # is already running this recipe (always resolvable).
        subprocess.run([sys.executable, "-c", shim], check=True, timeout=120, env=env)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        binp = os.path.join(self.cpp.build.bindirs[0], "test_cxxtest")
        # E077: OHOS only executes ELF files carrying a valid .codesign
        # section; a freshly built binary holds an unsigned placeholder that
        # must be removed before self-signing. On hosts without the signing
        # tools the binary runs unsigned (best effort, matches upstream use).
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        if os.path.isfile(signer) and os.path.isfile(objcopy):
            signer_env = {k: v for k, v in os.environ.items() if k != "LD_LIBRARY_PATH"}
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", binp],
                capture_output=True, timeout=60, env=signer_env,
            )
            signed = binp + ".signed"
            subprocess.run(
                [signer, "sign", "-inFile", binp, "-outFile", signed, "-selfSign", "1"],
                check=True, timeout=60, env=signer_env,
            )
            os.replace(signed, binp)
        os.chmod(binp, 0o755)
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "run_check.sh")
        self.run(f'{bash} "{script}" "{binp}"', env="conanrun")
