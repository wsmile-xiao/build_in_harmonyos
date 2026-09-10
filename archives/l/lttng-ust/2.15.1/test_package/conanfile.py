#!/usr/bin/env python3
"""Conan test_package for lttng-ust 2.15.1.

Compiles a consumer using tracef()/tracepoint macro, verifying liblttng-ust
links + initializes on OHOS.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import cross_building


class LttngUstTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        incs, libdirs = [], []
        for _r, _d in self.dependencies.items():
            incs += _d.cpp_info.includedirs
            libdirs += _d.cpp_info.libdirs
        inc = " ".join("-I" + p for p in dict.fromkeys(incs))
        link = " ".join(["-L" + p for p in dict.fromkeys(libdirs)]
                        + ["-llttng-ust", "-llttng-ust-tracepoint", "-lurcu", "-ldl", "-lpthread"]
                        + ["-Wl,-rpath," + p for p in dict.fromkeys(libdirs)])
        cc = "clang"
        for cand in ("clang", os.environ.get("CC", "")):
            if cand and shutil.which(cand):
                cc = cand
                break
        # OHOS musl 头需 _GNU_SOURCE 才声明 clock_gettime 等（urcu generic.h 用）
        self.run(f"{cc} -std=c11 -D_GNU_SOURCE test_lttng_ust.c -o test_lttng_ust_probe {inc} {link}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: only verifying compile+link")
            return
        self.run("./test_lttng_ust_probe", env="conanrun")
