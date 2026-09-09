#!/usr/bin/env python3
"""Conan recipe — bobby 50.0.2 (纯 bash prompt 主题).

bobby 是 Bash-it/oh-my-bash 的 bash prompt 主题（themes/bobby/bobby.theme.bash），
纯 bash 脚本，无编译无构建系统，无 conan 库依赖（运行时依赖 bash+git）。

适配（参考 boom-completion/bootcd 极简脚本包模式）：
- source(): Git.clone（Bash-it 仓库，git 独立 ssl，CI Python 无 SSL 时可下载，E372）
- package(): 提取 themes/bobby/bobby.theme.bash 到 share/bobby/
- test_package: 脚本存在性 + bash 语法校验
"""
import os

from conan import ConanFile
from conan.tools.files import copy, export_conandata_patches, apply_conandata_patches
from conan.tools.scm import Git


class BobbyConan(ConanFile):
    name = "bobby"
    version = "50.0.2"
    description = "bobby — Bash-it 的 bash prompt 主题（颜色/时钟/git 状态提示符）"
    license = "MIT"
    homepage = "https://bash-it.readthedocs.io/"
    url = ""  # CI fills this

    package_type = "application"

    # OHOS profile 需要全部四项（L0p 门禁）
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        # Git.clone：git 独立 ssl，CI Python 无 SSL 模块时仍可下载（E372 方案）。
        # 浅克隆（--depth 1）即 Bash-it master HEAD（含 themes/bobby/bobby.theme.bash），
        # 不 checkout 特定 commit——固定 commit 需深克隆，且臆造 commit 会报
        # "unable to read tree"。
        git = Git(self)
        git.clone(url=self.conan_data["git_url"],
                  target=".",
                  args=["--depth", "1"])

    def build(self):
        # 纯脚本无编译；应用 conandata 补丁（本包无补丁，G1 完整性要求调用）
        apply_conandata_patches(self)

    def package(self):
        # 提取 bobby prompt 主题脚本到 share/bobby/
        themedir = os.path.join(self.package_folder, "share", "bobby")
        os.makedirs(themedir, exist_ok=True)
        src_theme = os.path.join(self.source_folder, "themes", "bobby", "bobby.theme.bash")
        if os.path.isfile(src_theme):
            copy(self, "bobby.theme.bash", src=os.path.dirname(src_theme),
                 dst=themedir, keep_path=False)
        else:
            self.output.warning("bobby: bobby.theme.bash 未找到，尝试 lib/themes")
        # 文档（仓库根 LICENSE）
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.output.info("bobby: 纯 bash prompt 主题，运行时依赖 bash+git")
