#!/usr/bin/env python3
"""Conan test_package for ninja 1.13.2.

Consumer view: gets the installed ninja binary from the package, drives it to
compile a real C program with the OHOS clang toolchain, then runs the produced
binary and checks its observable output (R34: real API/product usage, not a
print-only shell).
"""
import os
import subprocess

from conan import ConanFile


class NinjaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_dir = os.path.join(self.dependencies["ninja"].package_folder, "bin")
        ninja_bin = os.path.join(bin_dir, "ninja")
        self.output.info(f"ninja binary: {ninja_bin}")

        # 1) Public CLI: version
        self.output.info("Running: ninja --version")
        self.run(f'"{ninja_bin}" --version', env="conanrun")

        # 2) Drive ninja to build a real C program with the OHOS clang.
        src = os.path.join(self.build_folder, "hello_ohos.c")
        with open(src, "w") as f:
            f.write(
                "#include <stdio.h>\n"
                "int main(void) {\n"
                "  printf(\"ohos-ninja-consumer-ok:%d\\n\", 3);\n"
                "  return 0;\n"
                "}\n"
            )
        build_ninja = os.path.join(self.build_folder, "build.ninja")
        import shutil
        cc = shutil.which("clang") or "/data/service/hnp/bin/clang"
        with open(build_ninja, "w") as f:
            f.write(
                f"rule cc\n"
                f"  command = {cc} $cflags -o $out $in\n"
                f"cflags = -O2\n"
                f"build hello_ohos: cc hello_ohos.c\n"
                f"default hello_ohos\n"
            )
        self.output.info("Running: ninja (build consumer program)")
        self.run(f'"{ninja_bin}" -C "{self.build_folder}"', env="conanrun")
        exe = os.path.join(self.build_folder, "hello_ohos")
        self.output.info("Running: consumer binary")
        out = subprocess.check_output([exe], text=True)
        self.output.info(f"consumer output: {out.strip()}")
        if "ohos-ninja-consumer-ok:3" not in out:
            raise RuntimeError(f"unexpected consumer output: {out!r}")