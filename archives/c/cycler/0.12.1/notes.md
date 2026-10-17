# cycler 0.12.1 适配笔记

## 编译环境
- 构建系统: python（纯 Python 包，无编译）
- 编译日期: 2026-08-29
- 状态: built（HarmonyOS 验证通过）
- 特殊说明: 纯 Python 包，无 .so、无 ELF 签名，不受 HMDFS/SELinux
  dlopen 限制；PyPI sdist **未打包测试**（测试在 GitHub 仓库）

## 库简介

cycler 是 matplotlib 的循环样式库，用于组合样式循环（color/linestyle 等）。
- 上游仓库: https://github.com/matplotlib/cycler
- 许可证: BSD-3-Clause
- 类型: 纯 Python（零运行时依赖——requires_dist 全部为 docs/tests extra）

## Conan 配方说明

### 配方结构
- `conanfile.py`: Conan 配方（纯 Python——source 下载 + build() staging
  copytree + package() 拷贝 cycler/ 到 site-packages）
- `conandata.yml`: PyPI sdist 下载 URL 和 SHA256
- `test_package/`: 消费者测试，验证 import cycler + cycler() 真实 API

### 关键配置
- `package_type = "python-require"`（typepy 模式——纯 Python 库，
  **不用 application**——R38 门禁对 application 要求 commands.json，
  python-require 无需 commands.json）
- 无 requires（PyPI requires_dist 全部为 docs/tests extra，运行时零依赖）
- build() staging 到 /data/storage/el2/base/cache（源外目录，
  build 内递归复制教训——typepy 同法）

## 依赖

无运行时依赖（docs/tests extra 不启用）。

## 测试说明

### 上游测试（实测，rule 4）
PyPI sdist **未打包测试**（tar tzf 核验：仅 cycler/ 包）——上游测试在
GitHub 仓库 test_cycler.py（24 个 test_ 函数，含 parametrize 展开）。
本地从 GitHub v0.12.1 tarball 实测 pytest **26 passed = 100%**。

### test_package 测试
- 文件: `test_package/test_cycler.py`
- 验证内容:
  1. import cycler（纯 Python 包）
  2. cycler() + cycler(color=...) 组合样式循环真实 API

## 验证结果

HarmonyOS 验证通过：上游 pytest 26/26（100%，GitHub tarball 实测），
Conan `test_package` 消费者测试 1/1。

## 注意事项

1. **纯 Python 特性**：无编译、无 .so，无需 ELF 签名/RPATH
2. **package_type**：用 python-require（非 application）——避免 R38
   commands.json 门禁
3. **测试来源**：PyPI sdist 未打包测试——上游测试用 GitHub tarball
   （rule 4 实测 26/26）
