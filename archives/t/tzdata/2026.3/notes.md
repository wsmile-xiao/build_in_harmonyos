# tzdata 2026.3 适配笔记

## 编译环境
- **构建系统**: setuptools（纯 Python 数据包，无编译）
- **编译日期**: 2026-08-31
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 0（无源码补丁）

## 编译步骤（conan create 全流程）

```bash
conan create archives/t/tzdata/2026.3 --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 从 conandata 声明的 PyPI sdist 下载并 strip_root。

### 2. 打包（package()）
- 纯 Python 数据包，无编译；无 CLI 入口 → `package_type=application`
  （本环境 python-require 型 conan create 静默跳过构建——实测 EXIT=0
  无产物，dataproperty/pytablewriter 同款先例）+ commands.json（R38）
- `build()` copytree 源码到 staging（源外目录），排除 egg-info/
  setup.py/test/docs 等非运行时文件
- **src/ 布局**：包在 `src/tzdata`（__init__.py + **zoneinfo 625 个时区
  数据文件** + zones），`package()` 复制到 `lib/python3.12/site-packages/`

## 依赖
- 零依赖（IANA 时区数据包，供 Python 3.9+ zoneinfo 模块使用）

## 上游测试（rule 4）
- 测试目录：tests/（pytest 套件：test_contents/test_version）
- 本地实测：**628/628（100%）**——30 passed + 598 subtests passed
  （subtest 为 test_load_zones 等参数化展开的最小测试单元），1.61s，
  零失败
- 适配后：test_package R34 真实 import 打包的 tzdata，用
  zoneinfo.ZoneInfo('Asia/Shanghai') 校验时区数据可用，1/1 = 100%

## 已知限制
- 无（纯 Python 数据包，zoneinfo 数据已随包打入）
