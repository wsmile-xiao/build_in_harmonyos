#!/usr/bin/env python3
"""Conan recipe — pip-completion 20200731 (pure Bash completion script, no compilation).

上游: https://github.com/ekalinin/pip-bash-completion (ekalinin/pip-bash-completion)
真实 recipe 参照: Homebrew Formula/p/pip-completion.rb（version 20200731 =
Homebrew 按 revision 日期自编，上游 tags 为空）。

包内容: 单个 bash 补全脚本 `pip`（861 字节，无 shebang、非可执行——由 bash
source 后通过 `complete -F _pip pip/pip2/pip3` 注册补全）。

OHOS 适配要点:
  - 上游 `make install` = `sudo cp pip /etc/bash_completion.d/`：需要 root 且
    写入共享系统前缀（R49 禁止）。改为安装到包内私有
    share/bash-completion/completions/pip，与已发布的 docker-completion/29.5.2、
    brew-cask-completion/2.1 完全同构。
  - 无任何 C/C++ 源码、无 configure/编译产物 → 不定义 build() 编译逻辑，
    仅在 build() 做源码存在性核验（不伪造编译日志）。
  - 无 conan 依赖：运行期由 bash（complete/compgen 内建）与 pip（被补全对象，
    由 python/3.12.9 提供）承担，二者均在设备/制品仓已可消费；
    bash-completion 仅为加载框架，同族先例均不声明 requires。
  - 无平台宏补丁需求（纯脚本，R8 无涉）；patches/ 为空。

R28: test_package/ 存在。
R34: test_package 真实 source 被测脚本并断言 `complete -p pip` 输出。
R38: 无可执行产物（只交付 share/ 下的数据脚本）→ 不声明 commands.json。
R51: 上游零自动化测试，声明见 test_package/MANIFEST.yml。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get)
from conan.tools.layout import basic_layout


class PipCompletionConan(ConanFile):
    name = "pip-completion"
    version = "20200731"
    description = "Bash completion for pip (commands and per-command options)"
    license = "MIT"
    homepage = "https://github.com/ekalinin/pip-bash-completion"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # code_style §2 要求显式声明包类型；纯脚本/数据包装配无库无可执行文件，
    # 取 conan 2.x 合法枚举 "unknown"（模板注释里的 "none" 不在枚举内，会报错）
    package_type = "unknown"

    # 无构建产物：脚本内容对 os/compiler/build_type/arch 完全无关
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        # 本版本无补丁（patches: {}），保留管道以与 CI 补丁流程同构
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 纯脚本包：无编译阶段。仅核验被测脚本确实存在且非空。
        apply_conandata_patches(self)
        script = os.path.join(self.source_folder, "pip")
        if not os.path.isfile(script):
            raise ConanException(f"Missing upstream completion script: {script}")
        size = os.path.getsize(script)
        if size < 100:
            raise ConanException(
                f"Upstream completion script unexpectedly small: {size} bytes")
        self.output.info(f"Completion script verified: pip ({size} bytes, no compilation needed)")

    def package(self):
        # 安装到包内私有的 bash-completion 目录（R49：禁止写 /etc 共享前缀）
        completions = os.path.join(self.package_folder, "share",
                                   "bash-completion", "completions")
        copy(self, "pip", src=self.source_folder, dst=completions, keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        # 数据/脚本包：与 os/compiler/arch 无关，单一 package_id
        self.info.clear()

    def package_info(self):
        # 补全脚本是数据文件：无库、无头文件、无可执行命令 → 不声明 commands.json
        # （R38；CI 侧 ci/conan/detect_bindirs.py 按 AST 判定返回 0，
        #   bin 目录显式置空以免 cpp_info 回落默认 ["bin"] 指向不存在的路径）
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.resdirs = ["share"]
