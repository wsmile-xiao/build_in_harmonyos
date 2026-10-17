#!/usr/bin/env python3
"""Conan test_package - compile and run a C consumer against the installed rure."""

import os
import re
import shlex
import subprocess
import time

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.layout import basic_layout


def real_cc(cc):
    """Follow the OHOS `clang` shell wrapper to the real ELF driver (clang-15)."""
    path = cc
    for _ in range(4):
        try:
            with open(path, "rb") as fh:
                if fh.read(4) == b"\x7fELF":
                    return path
            with open(path, "r", errors="replace") as fh:
                text = fh.read()
        except OSError:
            break
        body = "\n".join(l for l in text.splitlines() if not l.startswith("#!"))
        nxt = None
        for token in re.findall(r"/[^\s\"']+", body):
            try:
                with open(token, "rb") as fh:
                    if fh.read(4) == b"\x7fELF":
                        nxt = token
                        break
            except OSError:
                continue
        if not nxt:
            break
        path = nxt
    return path


class RureTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        env = Environment()
        env.define("CC", compilers.get("c", "clang"))
        env.vars(self, scope=None).save_script("consumer_env")

    def test(self):
        if not can_run(self):
            raise ConanInvalidConfiguration("The rure consumer must run on the target")
        raw_cc = self.conf.get("tools.build:compiler_executables", default={}).get("c", "clang")
        cc = real_cc(raw_cc)
        pkg = self.dependencies[self.tested_reference_str].package_folder
        inc = os.path.join(pkg, "include")
        lib = os.path.join(pkg, "lib", "librure.a")
        src = os.path.join(self.source_folder, "test.c")
        out = os.path.join(self.build_folder, "rure_consumer")
        cmd = [cc, "-O2", "-I", inc, src, lib, "-o", out, "-lpthread", "-ldl", "-lm"]
        env = {"PATH": "/data/service/hnp/bin:/usr/bin:/bin",
               "HOME": os.environ.get("HOME", ""),
               "TMPDIR": self.build_folder}
        last = ""
        for attempt in range(10):
            proc = subprocess.run(cmd, cwd=self.build_folder, env=env,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            if proc.returncode == 0:
                break
            last = proc.stdout or ""
            time.sleep(2 + attempt)
        else:
            raise ConanInvalidConfiguration("consumer build failed: %s" % last[-2000:])
        # OHOS requires the produced ELF to be signed before execution
        sign = os.path.join(os.path.dirname(raw_cc), "binary-sign-tool")
        signed = out + ".signed"
        subprocess.run([sign, "sign", "-inFile", out, "-outFile", signed, "-selfSign", "1"],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=True)
        os.chmod(signed, 0o755)
        self.run(shlex.join([signed]), env=["conanrun", "consumer_env"])
