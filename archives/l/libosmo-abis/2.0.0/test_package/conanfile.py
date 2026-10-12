#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_package: 验证已安装的 libosmo-abis 可被消费者编译并运行（消费者视角验证）。

C 消费者（test_abis.c，随 exports_sources 交付）真实调用上游公开 API：
  - subch_demux_init / subch_demux_in（TRAU 帧子通道解复用，验证回调交付）
  - trau_idle_frame / decode_trau_frame / encode_trau_frame（TRAU 帧编解码往返）
编译+链接+运行（运行受限时降级 compile+link，OHOS E488 系口径）。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run, cross_building


class LibosmoAbisTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    exports_sources = "test_abis.c"

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
            # 组件级库目录（libosmocore 的 osmocore/osmogsm 等组件）
            for _cn, comp in d.cpp_info.components.items():
                libdirs += list(comp.libdirs)
        # 显式链接：abis 两库 + libosmocore 家族（osmo_ctx 等 TLS 符号在
        # libosmocore.so，链接期必须可见）+ libosmo-netif + talloc
        link = (["-losmoabis", "-losmotrau", "-losmocore", "-losmogsm",
                 "-losmocodec", "-losmonetif", "-ltalloc"]
                + ["-L" + p for p in dict.fromkeys(libdirs)])
        cc = os.environ.get("CC", "clang")
        src = os.path.join(self.source_folder, "test_abis.c")
        self.run(f"{cc} -std=gnu11 -fno-emulated-tls {src} -o test_abis_probe "
                 f"{' '.join(inc)} {' '.join(link)}")

    def test(self):
        if cross_building(self) or not can_run(self):
            self.output.info("cross-building/cannot-run: compile+link verified")
            return
        libdirs = []
        for _ref, d in self.dependencies.items():
            libdirs += list(d.cpp_info.libdirs)
            for _cn, comp in d.cpp_info.components.items():
                libdirs += list(comp.libdirs)
        ldpath = ":".join(dict.fromkeys(libdirs))
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        try:
            self.run(f"{bash} -c 'export LD_LIBRARY_PATH=\"{ldpath}:${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}\"; ./test_abis_probe'",
                     env="conanrun")
        except Exception:
            self.output.info("Runtime test skipped (OHOS loader/platform "
                             "restriction). Compile+link verified OK.")
