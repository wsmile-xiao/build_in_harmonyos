#!/usr/bin/env python3
"""Conan recipe for fabric-completion 1.0 (pure data package).

Bash completion for Fabric (the Python deployment tool, fabfile.org):
a single bash script providing task and long-option completion for the
`fab` command. No compilation, no linking. Upstream is pinned to the
commit used by the Homebrew formula fabric-completion 1 (conan 版本号
取 "1.0"：真机 conan 2.29.1 拒绝裸单段版本号 "1"，见下方 version 注释)
(n0740/fabric-completion, commit 5b59104, MIT — the license text is
embedded in the script header; the tarball ships no separate LICENSE
file, so no licenses/ directory is created).

Layout follows the bash-completion ecosystem convention: the script is
installed to share/bash-completion/completions/ (Debian bash-completion
path convention; Homebrew installs it the same way, only renaming the
file to `fabric` — this package keeps the upstream filename, which is
also the path used in the upstream README's source instruction).

License: MIT.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get


class FabricCompletionConan(ConanFile):
    name = "fabric-completion"
    # 真机 conan 2.29.1 实测拒绝裸单段版本号 "1"（export 阶段
    # "Invalid package version '1'"）→ 归一化为 "1.0"（Homebrew
    # formula version 1 的 conan 合法形式，同版本语义不变）。
    version = "1.0"
    description = ("Bash completion for Fabric: fab task and long-option "
                   "completion script (pure data)")
    license = "MIT"
    homepage = "https://github.com/n0740/fabric-completion"
    url = ""  # CI fills this
    package_type = "unknown"

    # 纯数据/资源包：无编译、无链接，但保留 settings 以满足 CI L0 门禁的
    # 显式 settings 声明要求（与 kicad-demos 先例同款）。
    settings = "os", "compiler", "build_type", "arch"

    _completion_dir = os.path.join("share", "bash-completion", "completions")
    _doc_dir = os.path.join("share", "doc", "fabric-completion")

    # 上游 tarball 静态清单（Homebrew 公式同源 commit 5b59104，实测计数）。
    _files = ("README.md", "fabric-completion.bash")
    _expected_total = 2

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def export_sources(self):
        # 配方自足：源码与数据全部经 conandata sources（get）下载，
        # 除 conanfile.py/conandata.yml 外无本地文件需要随配方导出。
        pass

    def build(self):
        apply_conandata_patches(self)  # patches=[] 时为空操作，预留补丁入口
        # 纯数据包无编译步骤。构建期校验上游文件清单，防止下载内容或
        # 目录结构静默漂移（kicad-demos 先例范式）。
        missing = [f for f in self._files
                   if not os.path.isfile(os.path.join(self.source_folder, f))]
        if missing:
            raise ConanInvalidConfiguration(
                "fabric-completion 1.0 inventory drift: missing files "
                + ", ".join(missing)
            )
        total = sum(1 for _, _, files in os.walk(self.source_folder)
                    for f in files
                    if not f.endswith(".sh") and f != "conaninfo.txt")
        if total != self._expected_total:
            raise ConanInvalidConfiguration(
                f"fabric-completion 1.0 total file count {total} "
                f"!= {self._expected_total}"
            )

    def package(self):
        # 仅两个上游文件，显式复制（inform6-library/ldraw-parts 同款范式
        # 的简化版：文件少时逐文件复制比 copy("*")+excludes 更稳）。
        copy(self, "fabric-completion.bash", src=self.source_folder,
             dst=os.path.join(self.package_folder, self._completion_dir),
             keep_path=False)
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, self._doc_dir),
             keep_path=False)

    def package_info(self):
        self.cpp_info.resdirs = [self._completion_dir]
        self.cpp_info.libs = []
        # 无 runenv：bash-completion 生态无统一环境变量，消费者按上游
        # README 指引 source 该脚本（或复制到 ~/.bash_completion）。

    def package_id(self):
        self.info.clear()
