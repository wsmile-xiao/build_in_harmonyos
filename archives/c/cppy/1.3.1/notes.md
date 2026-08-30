# cppy 1.3.1 适配笔记

## 编译环境
- 构建系统: python（纯 Python 包，无编译）
- 编译日期: 2026-08-29
- 状态: built（HarmonyOS 验证通过）
- 特殊说明: 纯 Python 包 + C++ 头文件（cppy/cppy.h），无 .so，不受
  HMDFS/SELinux dlopen 限制

## 库简介

cppy 是供 Python C 扩展使用的 C++ 头文件库（`get_include()` 返回
`cppy/include` 路径，供扩展编译时 `#include <cppy/cppy.h>`）。
- 上游仓库: https://github.com/nucleic/cppy
- 许可证: BSD-3-Clause
- 类型: 纯 Python 包 + C++ 头文件（kiwisolver 同作者——kiwisolver
  build-system 依赖 cppy>=1.3.0，本包为 kiwisolver 前置构建依赖）

## Conan 配方说明

### 配方结构
- `conanfile.py`: Conan 配方（纯 Python——source 下载 + build() staging
  copytree + package() 拷贝 cppy/ 到 site-packages）
- `conandata.yml`: PyPI sdist 下载 URL 和 SHA256
- `test_package/`: 消费者测试，验证 import cppy + get_include()

### 关键配置
- `package_type = "python-require"`（typepy 模式——纯 Python 库，
  **不用 application**——R38 门禁对 application 要求 commands.json，
  python-require 无需 commands.json）
- 无 requires（PyPI requires_dist 仅 setuptools>=61.2，构建期 Python 自带）
- build() staging 到 /data/storage/el2/base/cache（源外目录，
  build 内递归复制教训——typepy 同法）

## 依赖

无外部依赖（setuptools 构建期由 Python 自带）。

## 测试说明

### 上游测试（实测，rule 4）
上游 tests/test_getting_include_dir.py 1 个测试（test_getting_include_directory），
本地实测 **1 passed = 100%**。

### test_package 测试
- 文件: `test_package/test_cppy.py`
- 验证内容:
  1. import cppy（纯 Python 包）
  2. cppy.get_include() 返回头文件目录，且 cppy/cppy.h 存在

## 验证结果

HarmonyOS 验证通过：上游 pytest 1/1（100%），Conan `test_package`
消费者测试 1/1。

## 注意事项

1. **纯 Python 特性**：无编译、无 .so，无需 ELF 签名/RPATH
2. **package_type**：用 python-require（非 application）——避免 R38
   commands.json 门禁
3. **kiwisolver 前置**：cppy/1.3.1 满足 kiwisolver build-system 的
   cppy>=1.3.0——后续适配 kiwisolver 时 requires 本包
