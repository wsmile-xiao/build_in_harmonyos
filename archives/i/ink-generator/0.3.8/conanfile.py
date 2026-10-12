#!/usr/bin/env python3
"""ink-generator 0.3.8 — ink!（Rust 智能合约）代码生成器（npm 包，wasm-bindgen 产物）。

上游是 **npm 包**：`ink_generator.js`（ESM 包装）+ `ink_generator_bg.js`（wasm-bindgen 胶水）
+ **预构建的 `ink_generator_bg.wasm`**（1.0 MB）+ `ink_generator.d.ts` + 两份许可 + README。

**版本说明（如实披露）**：比赛列表写的是 0.4，但 npm registry 上**没有 0.4**
（全部版本 0.3.1…0.3.8，latest = 0.3.8）→ 按既定规则用最新可获取版本 **0.3.8**。

依赖：**零依赖**（`dependencies: {}`）、无 `bin`/`scripts` → 无需在 build 期从 npm 源取依赖，
不存在"依赖缺口"。包内 wasm 是**预构建产物** → **不需要 Rust/wasm 工具链**
（与同属 Rust 系但必须 cargo 的 install-mimic 形成对照：后者在本环境系统级不可用）。

构建：**无编译步骤**。build() 只做基本自检（必需文件齐备 + wasm magic `\\0asm`），
真正的功能验证放在 test_package —— 用 **Node 端到端**加载 wasm 并调用 `start()`。

上游测试：仓库测试在 Rust 侧（cargo test），本环境无 Rust 工具链（rustup 拒绝 HarmonyOS）
→ 上游通过率记 **N/A** 并如实披露。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get
from conan.tools.layout import basic_layout

REQUIRED_FILES = ("ink_generator.js", "ink_generator_bg.js", "ink_generator_bg.wasm",
                  "ink_generator.d.ts", "package.json",
                  "LICENSE_APACHE", "LICENSE_MIT")


class InkGeneratorConan(ConanFile):
    name = "ink-generator"
    version = "0.3.8"
    description = ("ink! smart-contract code generator as a wasm-bindgen npm module "
                   "(prebuilt wasm, zero dependencies)")
    license = "Apache-2.0"        # 包内同时含 LICENSE_APACHE 与 LICENSE_MIT
    homepage = "https://github.com/Smart-Beaver/ink-generator-wasm"
    url = "https://github.com/Smart-Beaver/ink-generator-wasm"

    package_type = "application"   # 与同族 npm 包（acorn）一致
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        missing = [f for f in REQUIRED_FILES
                   if not os.path.isfile(os.path.join(self.source_folder, f))]
        if missing:
            raise ConanInvalidConfiguration(
                "npm 包内缺少必需文件：%s（上游包结构变化？）" % ", ".join(missing))
        wasm = os.path.join(self.source_folder, "ink_generator_bg.wasm")
        with open(wasm, "rb") as fh:
            magic = fh.read(4)
        if magic != b"\x00asm":
            raise ConanInvalidConfiguration("ink_generator_bg.wasm 不是合法 WASM（magic=%r）" % magic)
        self.output.info("[build] 无需编译：包内已含预构建 wasm（%d 字节），"
                         "必需文件 %d 个齐备（wasm-bindgen 产物）"
                         % (os.path.getsize(wasm), len(REQUIRED_FILES)))

    def package(self):
        res = os.path.join(self.package_folder, "res", self.name)
        os.makedirs(res, exist_ok=True)
        for name in REQUIRED_FILES + ("README.md",):
            src = os.path.join(self.source_folder, name)
            if os.path.isfile(src):
                shutil.copyfile(src, os.path.join(res, name))
        # 便于消费者定位：在包根也放一份许可
        for name in ("LICENSE_APACHE", "LICENSE_MIT"):
            src = os.path.join(self.source_folder, name)
            if os.path.isfile(src):
                shutil.copyfile(src, os.path.join(self.package_folder,
                                                  name.replace("LICENSE_", "LICENSE-")))
        self.output.info("[package] 安装 npm 模块到 res/%s/（%d 个文件）"
                         % (self.name, len(REQUIRED_FILES)))

    def package_info(self):
        # JS/wasm 模块没有 include/lib/bin 语义：模块文件放 res/ 供消费者引用
        self.cpp_info.resdirs = ["res"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
