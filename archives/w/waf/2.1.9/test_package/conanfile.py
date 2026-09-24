#!/usr/bin/env python3
"""Conan test_package for waf — verifies the waf build tool is installed and functional.

L1 consumer test (two levels):
1. `waf --version` — basic install/executable/version check
2. real mini-build (`waf configure build` with a rule-based wscript) —
   proves waf's configure/build contexts and task engine work on OHOS.
   Compiler-free by design: exercises waf itself, not the toolchain.
"""
import os
import tempfile

from conan import ConanFile

WSCRIPT = """top = '.'
out = 'build'

def configure(ctx):
    ctx.check_waf_version(mini_ver='2.1.0')

def build(ctx):
    ctx(rule='printf hello-waf > ${TGT}', target='out.txt', name='mini')
"""


class WafTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 1. Verify waf is available and reports its version
        self.run("waf --version", env="conanrun")

        # 2. Functional check: run a real (rule-based, compiler-free) build
        #    in a scratch dir so the test never pollutes the source tree
        #    (OHOS: tempfile uses $TMPDIR, /tmp itself is read-only)
        with tempfile.TemporaryDirectory() as workdir:
            with open(os.path.join(workdir, "wscript"), "w") as f:
                f.write(WSCRIPT)
            self.run("waf configure build", env="conanrun", cwd=workdir)
            out = os.path.join(workdir, "build", "out.txt")
            if not os.path.isfile(out):
                raise AssertionError("waf mini-build produced no output")
            with open(out) as f:
                content = f.read().strip()
            if content != "hello-waf":
                raise AssertionError(
                    "unexpected mini-build output: {!r}".format(content)
                )
