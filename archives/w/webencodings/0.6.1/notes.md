# webencodings 0.6.1 适配笔记

## 编译环境
- **构建系统**: setuptools（纯 Python，无编译）
- **编译日期**: 2026-08-31
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 0（无源码补丁）

## 编译步骤（conan create 全流程）

```bash
conan create archives/w/webencodings/0.6.1 --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 从 conandata 声明的 PyPI sdist 下载并 strip_root。

### 2. 打包（package()）
- 纯 Python 库，无编译；无 CLI 入口 → `package_type=application`
  （本环境 python-require 型 conan create 静默跳过构建——实测 EXIT=0
  无产物，dataproperty/pytablewriter 同款先例）+ commands.json（R38）
- `build()` copytree 源码到 staging（源外目录），排除 egg-info/
  setup.py/test/docs/mklabels.py 等非运行时文件
- `package()` 复制 `webencodings/`（3 个 .py）到 `lib/python3.12/site-packages/`

## 依赖
- 零依赖（上游 pyproject 仅 doc/test 可选依赖）

## 上游测试（rule 4）
- 测试目录：tests/test_webencodings.py（pytest 套件）
- 本地实测：**11 passed（100%）**——0.46s，零失败
- 适配后：test_package R34 真实 lookup('utf-8') 校验（1/1 = 100%）

## 已知限制
- 无（纯 Python 零依赖库）
