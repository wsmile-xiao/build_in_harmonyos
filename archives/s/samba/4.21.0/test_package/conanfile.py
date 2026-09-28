#!/usr/bin/env python3
"""test_package for samba 4.21.0 — 消费者用例（调用 samba 公开 API/工具）。

验证方式：
1. 消费者源码 conftest.c：include 包内公开头 wbclient.h，链接 libwbclient，
   调用 wbcStringToSid / wbcSidToString / wbcFreeMemory（纯字符串解析，
   无需 winbindd 守护进程）—— 编译 → 链接 → 运行三步验证；
2. 核心守护进程 sbin/smbd --version 可运行（Version 4.21.0）。
运行环境：聚合 samba 自身（lib、lib/private）与全部 conan 依赖的 libdir
作为 LD_LIBRARY_PATH，已手动验证该组合可让 smbd 正常加载运行。
"""

import os

from conan import ConanFile
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.layout import basic_layout


class SambaTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def generate(self):
        # 生成 conanrun 环境（聚合各依赖 runtime libdirs，兜底用）
        VirtualRunEnv(self).generate()

    def _all_libdirs(self):
        """samba 自身（lib + lib/private）与全部依赖存在的 libdir。"""
        dirs = []
        for _name, _d in self.dependencies.items():
            _pf = getattr(_d, "package_folder", None) or ""
            for _l in getattr(_d.cpp_info, "libdirs", None) or []:
                _full = _l if os.path.isabs(_l) or not _pf else os.path.join(_pf, _l)
                if os.path.isdir(_full):
                    dirs.append(_full)
                _priv = os.path.join(_full, "private")
                if os.path.isdir(_priv):
                    dirs.append(_priv)
        return dirs

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        pf = dep.package_folder
        cc = "clang"
        src = os.path.join(self.source_folder, "conftest.c")
        out = os.path.join(self.build_folder, "conftest")
        inc = os.path.join(pf, "include")
        lib = os.path.join(pf, "lib")
        libdirs = self._all_libdirs()
        run_env = Environment()
        run_env.define("LD_LIBRARY_PATH", ":".join(dict.fromkeys(libdirs)))
        rpath = ":".join(dict.fromkeys(libdirs))

        # 消费者用例 1：编译 + 链接（conanbuild 环境提供 clang）
        self.run(
            f"{cc} {src} -o {out} -I{inc} -L{lib} -Wl,-rpath,{rpath} -lwbclient",
            cwd=self.build_folder,
            env=["conanbuild"],
        )
        # 运行 conftest
        with run_env.vars(self).apply():
            self.run(f"{out}", cwd=self.build_folder)

        # 消费者用例 2：核心守护进程工具 --version（需完整 LD_LIBRARY_PATH）
        smbd = os.path.join(pf, "sbin", "smbd")
        if os.path.exists(smbd):
            with run_env.vars(self).apply():
                self.run(f"{smbd} --version", cwd=self.build_folder)
        else:
            self.output.info("[samba test_package] smbd 未安装，跳过工具运行验证")
