#!/usr/bin/env python3
"""Conan test_package for chromono 1.1.3 (application).

chromono 是 SDL2/GLES2 图形益智游戏：main() 在创建 SDL 窗口/GL 上下文之前没有任何
可独立验证的 CLI 路径，且对无显示环境零容错（SDL_CreateWindow 失败即走空指针崩溃
路径）。因此本 test_package 用配方新增的最小 --version 冒烟入口（0002 patch，位于
main() 最前、先于任何 SDL/显示初始化）验证"二进制可加载 + 共享依赖(SDL2/
libvorbisfile/libogg/zlib)可解析 + ELF 已自签"：

  - 正例：chromono --version → 退出码 0 且输出含 "chromono 1.1.3"；
随后对真实启动做一次限时探测：若进程存活到超时（进入游戏主循环）即完整 GUI 冒烟
通过；若在 headless 下于显示/GL 初始化处退出，则如实记录 GUI 验证边界（非适配
缺陷，不虚构成功）。

具体断言逻辑在 test_chromono.sh（L0c 门禁要求 test_package 下有测试源文件）。
"""
import os

from conan import ConanFile


class ChromonoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if self.settings.os not in ("Linux", "OHOS"):
            return

        pkg = self.dependencies["chromono"].package_folder
        exe = os.path.join(pkg, "bin", "chromono")
        assert os.path.isfile(exe), f"chromono not found at {exe}"

        # 输出用临时目录，避免把 version.out/run.out 写入 repo 的 test_package/
        # （conan create 时 build_folder 与 source 相关，直接写会污染工作树）
        import tempfile
        test_script = os.path.join(self.source_folder, "test_chromono.sh")
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        with tempfile.TemporaryDirectory() as out_dir:
            self.run(f'{bash} "{test_script}" "{exe}" "{out_dir}"', env="conanrun")
