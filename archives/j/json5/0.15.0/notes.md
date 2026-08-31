# json5 0.15.0 适配笔记

## 编译环境
- **构建系统**: setuptools（纯 Python，无编译）
- **编译日期**: 2026-08-31
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 0（无源码补丁）

## 编译步骤（conan create 全流程）

```bash
conan create archives/j/json5/0.15.0 --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 从 conandata 声明的 PyPI sdist 下载并 strip_root。

### 2. 打包（package()）
- 纯 Python 库，无编译；无 CLI 入口 → `package_type=application`
  （本环境 python-require 型 conan create 静默跳过构建——实测 EXIT=0
  无产物，dataproperty/pytablewriter 同款先例）+ commands.json（R38）
- `build()` copytree 源码到 staging（源外目录），排除 egg-info/
  setup.py/test/sample 等非运行时文件
- `package()` 复制 `json5/`（7 个 .py）到 `lib/python3.12/site-packages/`

## 依赖
- 零依赖（上游 pyproject 无 install_requires）

## 上游测试（rule 4）
- 测试目录：tests/（pytest 套件：lib_test/host_test/tool_test）
- 本地实测：**75/75（100%）**——2.83s，零失败（tool_test 含子进程测试，
  注入 PYTHONPATH 后全过）
- 适配后：test_package R34 真实 import 打包的 json5 并解析 JSON5
  字符串（注释+尾逗号），1/1 = 100%

## 已知限制
- 无（纯 Python 零依赖库）
