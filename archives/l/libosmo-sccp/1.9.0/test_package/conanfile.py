#!/usr/bin/env python3
"""Conan test_package for libosmo-sccp 1.9.0 — 消费者视角验证（L1）。

C 消费者（test_sccp.c，随 exports_sources 交付）真实调用 libosmo-sigtran
公开 API：
  - osmo_ss7_instance_find_or_create / osmo_ss7_instance_find（实例创建/查询）
  - osmo_ss7_asp_find_or_create2 / osmo_ss7_asp_get_proto|get_trans_proto（ASP）
  - osmo_ss7_as_find_or_create / osmo_ss7_as_add_asp / osmo_ss7_as_del_asp（AS）
  - osmo_ss7_asp_destroy / osmo_ss7_as_destroy / osmo_ss7_instance_destroy（析构）
编译+链接+运行（运行受限时降级 compile+link，OHOS E488 系口径）。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run, cross_building


class LibosmoSccpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    exports_sources = "test_sccp.c"

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
            for _cn, comp in d.cpp_info.components.items():
                libdirs += list(comp.libdirs)
        # 显式链接：sigtran 本体 + libosmocore 家族 + netif + talloc
        # （osmo_ctx 等 TLS 符号在 libosmocore.so，链接期必须可见）
        link = (["-losmo-sigtran", "-losmocore", "-losmovty", "-losmogsm",
                 "-losmonetif", "-ltalloc"]
                + ["-L" + p for p in dict.fromkeys(libdirs)])
        # 编译器发现链（R33 精神，不硬编码单机路径）：CC 环境变量 →
        # PATH 中的 clang（OHOS toolchain 已注入 PATH）→ 默认 clang
        cc = os.environ.get("CC") or shutil.which("clang") or "clang"
        src = os.path.join(self.source_folder, "test_sccp.c")
        self.run(f"{cc} -std=gnu11 -fno-emulated-tls {src} -o test_sccp_probe "
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
        bash = os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL") or "/bin/sh"
        # 真实运行：失败必须向上传播（失败即 fail），不做 catch-all 吞异常
        # （跨平台无法运行的情形已由上方 cross_building/can_run 守卫覆盖）
        self.run(f"{bash} -c 'export LD_LIBRARY_PATH=\"{ldpath}:${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}\"; ./test_sccp_probe'",
                 env="conanrun")
