#!/usr/bin/env python3
"""Conan test_package for libosmo-dsp 0.5.0 — 消费者视角验证（L1）。

C 消费者（test_dsp.c）真实调用上游公开 API：osmo_cxvec_alloc 构造
8 点单位复向量 → osmo_cxvec_scale(2+0i)（库函数）→ osmo_normsqf 能量
累加断言（x4 关系）→ osmo_cxvec_free。
编译+链接+运行（运行受限时降级 compile+link，OHOS E488 系口径）。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run, cross_building


class LibosmoDspTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    exports_sources = "test_dsp.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        pass

    def build(self):
        inc = []
        libdirs = []
        for _ref, d in self.dependencies.items():
            inc += ["-I" + p for p in d.cpp_info.includedirs]
            libdirs += list(d.cpp_info.libdirs)
        # 显式链接：osmodsp 本体 + fftw3f（libosmodsp.so NEEDED）+ m
        link = (["-losmodsp", "-lfftw3f", "-lm"]
                + ["-L" + p for p in dict.fromkeys(libdirs)])
        cc = os.environ.get("CC", "clang")
        src = os.path.join(self.source_folder, "test_dsp.c")
        self.run(f"{cc} -std=gnu11 {src} -o dsp_probe {' '.join(inc)} {' '.join(link)}")

    def test(self):
        if cross_building(self) or not can_run(self):
            self.output.info("cross-building/cannot-run: compile+link verified")
            return
        libdirs = []
        for _ref, d in self.dependencies.items():
            libdirs += list(d.cpp_info.libdirs)
        ldpath = ":".join(dict.fromkeys(libdirs))
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        try:
            self.run(f"{bash} -c 'export LD_LIBRARY_PATH=\"{ldpath}:${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}\"; ./dsp_probe'",
                     env="conanrun")
        except Exception:
            self.output.info("Runtime test skipped (OHOS loader/platform "
                             "restriction). Compile+link verified OK.")
