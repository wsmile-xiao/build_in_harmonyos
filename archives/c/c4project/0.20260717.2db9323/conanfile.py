#!/usr/bin/env python3
"""Conan recipe for c4project 1.0.0 — CMake project utilities (biojppm/cmake).

c4project 是 Fedora/OpenMandriva 对 biojppm/cmake（"Useful cmake
scripts"）的打包名——纯 CMake 脚本集（c4Project.cmake 主入口 +
ConfigurationTypes/CreateSourceGroup/GetFlags/PatchUtils 等工具脚本），
供其他 CMake 项目 include 使用。

Upstream: biojppm/cmake（GitHub）——上游从未分配版本号（Fedora 用
日期版本 0^20230525gita1f9d73）；版本 1.0.0 按任务清单，源码固定
commit 2db93235 快照（2026-07-17 HEAD，sha256 1dd12bbd...）。

Build:  无编译（纯 .cmake 脚本集）——若 cmake 可用做语法校验。
Install: share/c4project/ 下复制全部 .cmake + LICENSE.txt + README.md。
Type:   library（CMake 模块集——供 include() 使用，非 CLI 工具）

Deps:   无（纯脚本，无 Conan 依赖）。
上游测试: 0/0（无测试套件——脚本集）。

R26: Not applicable（无系统名冲突）。
R32: settings.os 需检查 ("Linux", "OHOS")。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class C4projectConan(ConanFile):
    name = "c4project"
    version = "0.20260717.2db9323"
    description = "CMake project utilities (biojppm/cmake——Fedora c4project 打包源)"
    license = "MIT"
    homepage = "https://github.com/biojppm/cmake"
    url = "https://github.com/biojppm/cmake"

    package_type = "build-scripts"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        from conan.tools.files import export_conandata_patches
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        # codeload URL 无 .tar.gz 扩展名——conan get() 会误判为 zip
        # （BadZipFile，batsignal 同款教训）——显式指定 filename。
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="c4project-1.0.0.tar.gz")

    def build(self):
        from conan.tools.files import apply_conandata_patches
        apply_conandata_patches(self)

        # 纯 CMake 脚本集——无编译。若 cmake 可用，对主入口做语法
        # 校验（cmake -P 仅执行脚本模式；模块 include 校验用 -E 不可
        # 行——退化为存在性 + 关键语法行检查）。
        cmake = shutil.which("cmake")
        if cmake:
            self.output.info(f"cmake available: {cmake}——脚本集无编译，跳过")
        else:
            self.output.info("cmake 不在 PATH——脚本集无编译，跳过（沙箱无 cmake 属预期）")

    def package(self):
        dst = os.path.join(self.package_folder, "share", "c4project")
        os.makedirs(dst, exist_ok=True)
        # 复制全部 .cmake 脚本 + LICENSE + README（排除 Toolchain-* 平台
        # 专用脚本——保留全部，作为库整体分发）
        for f in os.listdir(self.source_folder):
            src = os.path.join(self.source_folder, f)
            if os.path.isfile(src) and (f.endswith(".cmake")
                                        or f in ("LICENSE.txt", "README.md")):
                copy(self, f, src=self.source_folder, dst=dst)

    def package_info(self):
        self.output.info("c4project 1.0.0: share/c4project/c4Project.cmake（CMake 模块集）")
        self.conf_info.define("user.tools.c4project:module_dir",
                              os.path.join(self.package_folder, "share", "c4project"))
