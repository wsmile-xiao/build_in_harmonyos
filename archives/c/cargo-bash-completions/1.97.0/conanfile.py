#!/usr/bin/env python3
"""Conan recipe — cargo-bash-completions 1.97.0 (pure Bash completion script, no compilation).

上游: https://github.com/rust-lang/cargo （Rust 官方 cargo 仓库，Apache-2.0 OR MIT 双许可）
交付物: 上游 `src/etc/cargo.bashcomp.sh` —— cargo 命令的 bash 补全脚本
        （311 行 / 11443 字节，无 shebang、非可执行，供 bash `source` 加载）。

版本号口径（R37）:
  包版本 1.97.0 = cargo CLI 对外版本（`cargo --version` 输出 `cargo 1.97.0`，随
  Rust 1.97.0 一同分发）。rust-lang/cargo 的 crate/tag 版本恒比其所属 Rust 发行版
  **大** 一个 minor —— 上游 `src/doc/contrib/src/process/release.md` 原文：
  "The minor version is always 1 greater than the Rust release it is a part of,
   so cargo 0.49.0 is part of the 1.48 Rust release."
  因此 CLI 1.97.0 对应仓库 tag `0.98.0`（不是 `0.97.0`，后者属 Rust 1.96）。
  交叉验证：rust-lang/rust tag `1.97.0` 的 `src/tools/cargo` submodule 指向
  commit `c980f4866141969fab6254a680546a277789d6f0` = cargo tag `0.98.0`；
  且 `0.98.0` 的脚本含 1.97 新增的 `-m --manifest-path` 短选项（`0.97.0` 没有），
  test_package 的 A8 断言对此做实证。

OHOS 适配要点:
  - **本包不编译任何 Rust 代码**：只从上游源码树取出一个 bash 脚本作为数据文件安装，
    构建机/CI 无需 rustc/cargo 工具链（与需要 cargo 构建的 Rust 应用包性质不同）。
  - 上游没有安装该脚本的 make 目标（Rust 官方发行版由 rust-installer 把它装成
    `etc/bash_completion.d/cargo`）。本配方按 bash-completion 规范安装到包内私有
    `share/bash-completion/completions/cargo`（文件名 = 被补全命令名，便于框架按需加载），
    不写 `/etc` 等共享系统前缀（R49）。
  - 无 C/C++ 源码、无 configure/编译产物 → 不定义编译逻辑；build() 只做源码核验，
    不伪造编译日志。脚本内容与 os/compiler/build_type/arch 完全无关。
  - 无 conan 依赖：运行期由 bash（`complete`/`compgen` 内建）、cargo（被补全对象）、
    以及 bash-completion 框架（`_get_comp_words_by_ref`/`_filedir`）承担；同族已发布先例
    docker-completion / pip-completion / brew-cask-completion 同样不声明 requires。
  - 纯脚本包，无平台宏需求（R8 无涉），patches/ 为空。

R28: test_package/ 存在。
R32: 无 `settings.os` 分支逻辑（脚本与平台无关），不涉及 Linux/OHOS 判定。
R34: test_package 真实 `source` 被测脚本并断言 `complete -F _cargo cargo` 注册与补全候选实际生成。
R38: 无可执行产物（只交付 share/ 下的数据脚本）→ 不声明 commands.json。
R51: 上游对该脚本零自动化测试（清点证据见 test_package/MANIFEST.yml 与 notes.md）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get, load, rename)
from conan.tools.layout import basic_layout


class CargoBashCompletionsConan(ConanFile):
    name = "cargo-bash-completions"
    version = "1.97.0"
    description = "Bash completion script for the cargo command (subcommands, options, toolchains)"
    license = "Apache-2.0 OR MIT"
    homepage = "https://github.com/rust-lang/cargo"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("cargo", "rust", "bash-completion", "shell")

    # code_style §2: 显式声明包类型。纯脚本/数据包既无库也无可执行文件，
    # 取 conan 2.x 合法枚举 "unknown"（同族先例 pip-completion 同口径）
    package_type = "unknown"

    # PF8 要求 settings 四项齐全；产物本身对四项均无关（见 package_id）
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        # 本版本无补丁（patches: {}），保留管道以与 CI 补丁流程同构
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        # 纯脚本包：无编译阶段。核验被交付脚本存在、大小合理、补全注册语句未被上游移除。
        apply_conandata_patches(self)
        script = os.path.join(self.source_folder, "src", "etc", "cargo.bashcomp.sh")
        if not os.path.isfile(script):
            raise ConanException(f"Missing upstream completion script: {script}")
        size = os.path.getsize(script)
        if size < 4096:
            raise ConanException(
                f"Upstream completion script unexpectedly small: {size} bytes")
        content = load(self, script)
        if "complete -F _cargo cargo" not in content:
            raise ConanException(
                "Upstream script no longer registers `complete -F _cargo cargo`; "
                "packaging aborted to avoid shipping a non-functional completion")
        self.output.info(
            f"Completion script verified: cargo.bashcomp.sh ({size} bytes, no compilation needed)")

    def package(self):
        # 安装到包内私有 bash-completion 目录（R49：不写 /etc 等共享前缀）
        completions = os.path.join(self.package_folder, "share",
                                   "bash-completion", "completions")
        copy(self, "cargo.bashcomp.sh",
             src=os.path.join(self.source_folder, "src", "etc"),
             dst=completions, keep_path=False)
        # bash-completion 规范：补全文件名 = 被补全命令名，与 Rust 官方发行版的
        # etc/bash_completion.d/cargo 一致
        rename(self, os.path.join(completions, "cargo.bashcomp.sh"),
               os.path.join(completions, "cargo"))
        for lic in ("LICENSE-APACHE", "LICENSE-MIT"):
            copy(self, lic, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        # 数据/脚本包：与 os/compiler/build_type/arch 无关，单一 package_id
        self.info.clear()

    def package_info(self):
        # 补全脚本是数据文件：无库、无头文件、无可执行命令 → 不声明 commands.json（R38）。
        # bindirs 显式置空，避免 cpp_info 回落默认 ["bin"] 指向不存在的目录。
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.resdirs = ["share"]
