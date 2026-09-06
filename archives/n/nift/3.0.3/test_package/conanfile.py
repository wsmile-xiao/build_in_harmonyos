#!/usr/bin/env python3
"""Conan test_package — nift 3.0.3（消费者功能测试，R34：真实执行被测二进制）。

nift 是命令行工具（无库可链接）：消费者测试真实执行打包的 nift/nsm 二进制。
上游 v3.0.3 无测试套件（Makefile 无 check/test 目标、仓库无 tests/ 目录），
故以 test_nift.sh 的 11 项功能断言代替（每个断言都真实调用打包产物）：
  1. `nift --version` 输出含 3.0.3
  2. `nsm --version` 输出含 3.0.3（双入口一致）
  3. `nift init-html` 构建最小静态网站 output/index.html
  4. init-html 静态资源（assets/css、assets/js）镜像到 output/
  5. 站点生成 E2E：`nift track` 自定义模板页面 + `nift build` → 模板被选中
  6. 模板变量 $[title] 被替换为页面标题
  7. @content 注入页面正文
  8. 多页面独立产出（beta.html）
  9. 增量构建（hash 模式）：内容修改后重构建替换旧输出
  10. 内嵌 Lua 引擎：`nift run` 执行 Lua 脚本输出预期文本
  11. `nift init` 通用项目初始化并构建 output/index.html
"""

import os

from conan import ConanFile


class NiftTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # CONFIG_SHELL 由 ci/conan/profiles/ohos-aarch64 [buildenv] 注入
        # （=/data/service/hnp/bin/bash）。fallback 为该构建环境的固定 bash 路径：
        # OHOS 默认 /system/bin/sh 无法可靠执行 ELF，须用 bash 包装执行测试脚本。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test_nift.sh", env="conanrun")
