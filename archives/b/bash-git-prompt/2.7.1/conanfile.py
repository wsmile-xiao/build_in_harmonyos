#!/usr/bin/env python3
"""Conan recipe for bash-git-prompt 2.7.1 — informative git prompt for bash.

上游：https://github.com/magicmonty/bash-git-prompt（v2.7.1）
构建：无编译（纯 Bash 脚本集——gitprompt.sh 主脚本 + gitstatus.sh/py +
      prompt-colors.sh + themes/——bashrc 中 source gitprompt.sh 使用）
上游测试：无测试套件（46 文件无 test/bats——如实 0/0）——
      消费测试：source gitprompt.sh 真实加载（bash 语法 + 函数定义检查）
运行依赖：git（OHOS 已有 git 2.45.2——>=1.7.10 满足）
"""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class BashGitPromptConan(ConanFile):
    name = "bash-git-prompt"
    version = "2.7.1"
    description = "Informative git prompt for bash and fish (pure Bash scripts)"
    license = "BSD-2-Clause"
    homepage = "https://github.com/magicmonty/bash-git-prompt"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        # codeload URL 无 .tar.gz 扩展名——conan get() 按扩展名误判为 zip
        # （BadZipFile）——显式 filename 指定（buildessential 同款坑）
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="bash-git-prompt-2.7.1.tar.gz")

    def build(self):
        # 上游无测试套件（46 文件无 test/bats 目录）——如实记录 0/0
        self.output.info("BASH-GIT-PROMPT UPSTREAM TEST PASS/FAIL: 0/0 "
                         "(上游无测试套件——如实记录)")

    def package(self):
        # 复制全部脚本 + themes + LICENSE（纯脚本分发——无编译）
        for f in ["gitprompt.sh", "gitstatus.sh", "gitstatus.py",
                  "gitstatus_pre-1.7.10.sh", "git-prompt-help.sh",
                  "prompt-colors.sh", "gitprompt.fish"]:
            copy(self, f, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "share", "bash-git-prompt"))
        copy(self, "themes/*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "bash-git-prompt", "themes"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        # 脚本默认在 gitprompt.sh 同目录找 gitstatus.sh/themes——
        # 通过 __GIT_PROMPT_DIR 环境变量可指向安装目录
        self.env_info.__GIT_PROMPT_DIR = os.path.join(
            self.package_folder, "share", "bash-git-prompt")
