#!/usr/bin/env python3
"""Conan test_package — lisgd 0.3.7 (application: run the packaged CLI, assert behavior).

上游测试清点（R51，证据见本目录 MANIFEST.yml）：lisgd 0.3.7 **上游无测试套件**——
tarball 内 7 个文件无 tests/ 目录，Makefile 目标仅 all/options/.c.o/config.h/lisgd/
install/clean，无 check/test 目标（实测 `make check` / `make test` 均报
"No rule to make target"）⇒ N_static=0，按规则以消费者测试补位：真实执行被测包
安装的 lisgd 二进制并断言行为。
"""
import os

from conan import ConanFile


class LisgdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _host_libdirs(self):
        """聚合全部 host 依赖（含传递）的 lib 目录。

        依据同仓 dmenu 5.4 test_package：归档依赖包的 cpp_info 未必让 conanrun.sh
        注入 LD_LIBRARY_PATH，缺失时 lisgd 启动即报
        `Error loading shared library libinput.so.10`（B 机裸跑复现同一串）。
        """
        dirs = []
        for dep in self.dependencies.host.values():
            pf = dep.package_folder
            if not pf:
                continue
            for sub in ("lib", "lib64"):
                d = os.path.join(str(pf), sub)
                if os.path.isdir(d):
                    dirs.append(d)
        return dirs

    def test(self):
        if str(self.settings.os) != "OHOS":
            self.run("sh test.sh", env="conanrun")
            return

        libdirs = self._host_libdirs()
        # 覆盖既有 LD_LIBRARY_PATH 而非追加：conanrun.sh 注入的包内 lib 优先级
        # 保持不变（包内无 .so，仅 bindirs），依赖 .so 全部来自下方聚合目录。
        prefix = 'export LD_LIBRARY_PATH="%s"; ' % ":".join(libdirs)
        self.run(prefix + "sh test.sh", env="conanrun")
