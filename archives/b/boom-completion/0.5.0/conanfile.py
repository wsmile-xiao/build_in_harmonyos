#!/usr/bin/env python3
"""Conan recipe — boom-completion 0.5.0 (纯 Shell 补全脚本).

boom-completion 是 holman/boom（Ruby CLI）的 bash/zsh 补全脚本：
- completion/boom.bash（17 行，bash 补全，定义 _boom_complete）
- completion/boom.zsh（29 行，zsh 补全，定义 _boom）

纯脚本无编译无构建系统无依赖；package() 直接把两个补全脚本复制到包内
补全目录（bash 补全按惯例放 share/bash-completion/completions/，
zsh 补全放 share/zsh/site-functions/，参考 Homebrew formula 的
bash_completion/zsh_completion install）。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches


class BoomCompletionConan(ConanFile):
    name = "boom-completion"
    version = "0.5.0"
    description = "Bash 和 Zsh 的 boom CLI 补全脚本"
    license = "MIT"
    homepage = "https://zachholman.com/boom/"
    url = ""  # CI fills this

    package_type = "application"

    # OHOS profile 需要全部四项（L0p 门禁）
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        # 纯脚本包，无构建；用简单 layout（不做构建目录隔离）
        self.folders.source = "."
        self.folders.build = "."

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 纯脚本无编译；应用 conandata 补丁（本包无补丁，G1 完整性要求调用）
        apply_conandata_patches(self)

    def package(self):
        # bash 补全 → share/bash-completion/completions/boom（bash 补全惯例
        # 文件名不带扩展名，参考 Homebrew formula 的 bash_completion.install
        # "completion/boom.bash" => "boom"）
        bash_dir = os.path.join(self.package_folder, "share",
                                "bash-completion", "completions")
        os.makedirs(bash_dir, exist_ok=True)
        copy(self, "boom.bash", src=os.path.join(self.source_folder, "completion"),
             dst=bash_dir, keep_path=False)
        os.rename(os.path.join(bash_dir, "boom.bash"),
                  os.path.join(bash_dir, "boom"))
        # zsh 补全 → share/zsh/site-functions/_boom（zsh 补全按惯例带 _ 前缀）
        zsh_dir = os.path.join(self.package_folder, "share", "zsh", "site-functions")
        os.makedirs(zsh_dir, exist_ok=True)
        copy(self, "boom.zsh", src=os.path.join(self.source_folder, "completion"),
             dst=zsh_dir, keep_path=False)
        os.rename(os.path.join(zsh_dir, "boom.zsh"),
                  os.path.join(zsh_dir, "_boom"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # 纯数据包（补全脚本），无库/无头文件；暴露补全目录路径供消费者引用
        self.output.info("boom-completion: bash 补全与 zsh 补全脚本已打包")
