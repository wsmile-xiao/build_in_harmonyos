# loguru 0.7.3 适配笔记

## 编译环境
- **构建系统**: setuptools（纯 Python，无编译）
- **编译日期**: 2026-08-31
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 0（无源码补丁）

## 编译步骤（conan create 全流程）

```bash
conan create archives/l/loguru/0.7.3 --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 从 conandata 声明的 PyPI sdist 下载并 strip_root。

### 2. 打包（package()）
- 纯 Python 库，无编译；无 CLI 入口 → `package_type=application`
  （本环境 python-require 型 conan create 静默跳过构建——实测 EXIT=0
  无产物，dataproperty/pytablewriter 同款先例）+ commands.json（R38）
- `build()` copytree 源码到 staging（源外目录），排除 egg-info/
  setup.py/test 等非运行时文件
- `package()` 复制 `loguru/`（约 15 个 .py）到
  `lib/python3.12/site-packages/`

## 依赖
- 上游依赖均条件性：colorama/win32-setctime 仅 win32、aiocontextvars
  仅 python<3.7——**OHOS（Python 3.12 / Linux）下零运行时依赖**

## 上游测试（rule 4）
- 测试目录：tests/（pytest 套件；sdist 不含 tests/，测试取自
  GitHub v0.7.3 tag）
- 本地实测：**1554 passed / 10 failed / 28 skipped**（99.36%，
  28 skipped 不计分母）
- 两轮修复：①mypy 1.13.0（上游固定版本）清零 44 个 typesafety 失败；
  ②剩余 10 个 test_filesink_permissions 失败为沙箱文件系统不保留精确
  权限位（os.open 指定 0o777 实际 0o770）——环境阻塞，非库缺陷
  （rule 5.2 如实记录）
- 适配后：test_package R34 真实 import 打包的 loguru，logger 记录经
  list sink 捕获校验，1/1 = 100%

## 已知限制
- 无（纯 Python，OHOS 下零依赖日志库）
