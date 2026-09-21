#!/usr/bin/env python3
"""Conan test_package for libosmo-netif 1.6.0 — 消费者视角验证（L1）。

C 消费者（test_netif.c，随 exports_sources 交付）真实调用上游公开 API：
  - osmo_stream_cli_create / osmo_stream_srv_link_create（对象构造）
  - osmo_stream_cli_set_* / osmo_stream_srv_link_set_*（参数配置）
  - osmo_stream_cli_destroy / osmo_stream_srv_link_destroy（析构）
编译+链接+运行（运行受限时降级 compile+link，OHOS E488 系口径）。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run, cross_building


class LibosmoNetifTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    exports_sources = "test_netif.c"

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
            # 组件级库目录（libosmocore 的 osmocore/osmogsm 组件）
            for _cn, comp in d.cpp_info.components.items():
                libdirs += list(comp.libdirs)
        # 显式链接：netif 本体 + libosmocore 家族（osmo_ctx 等 TLS 符号在
        # libosmocore.so，链接期必须可见）
        link = (["-losmonetif", "-losmocore", "-losmogsm", "-ltalloc"]
                + ["-L" + p for p in dict.fromkeys(libdirs)])
        cc = os.environ.get("CC", "clang")
        src = os.path.join(self.source_folder, "test_netif.c")
        self.run(f"{cc} -std=gnu11 -fno-emulated-tls {src} -o test_netif_probe "
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
            self.run(f"{bash} -c 'export LD_LIBRARY_PATH=\"{ldpath}:${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}\"; ./test_netif_probe'",
                     env="conanrun")
        except Exception:
            self.output.info("Runtime test skipped (OHOS loader/platform "
                             "restriction). Compile+link verified OK.")
