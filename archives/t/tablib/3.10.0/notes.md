# tablib 3.10.0 适配笔记

## 编译环境
- **构建系统**: setuptools（纯 Python，无编译）
- **编译日期**: 2026-08-31
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 0（无源码补丁）

## 编译步骤（conan create 全流程）

```bash
conan create archives/t/tablib/3.10.0 --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 从 conandata 声明的 PyPI sdist 下载并 strip_root。

### 2. 打包（package()）
- 纯 Python 库，无编译；无 CLI 入口 → `package_type=application`
  （本环境 python-require 型 conan create 静默跳过构建——实测 EXIT=0
  无产物，dataproperty/pytablewriter 同款先例）+ commands.json（R38）
- `build()` copytree 源码到 staging（源外目录），排除 egg-info/
  setup.py/test/docs 等非运行时文件
- **src/ 布局**：包在 `src/tablib`（core.py + exceptions.py + formats/
  + utils.py + _vendor/），`package()` 复制到
  `lib/python3.12/site-packages/`

## 依赖
- 核心零运行时依赖（pyproject dependencies 为空）；各 format（csv/
  xlsx/dbf 等）的第三方依赖均为可选 extras，不随核心包引入

## 上游测试（rule 4）
- 测试目录：tests/（pytest 套件：test_tablib.py 等）
- 本地实测：**183/183（100%）**——6.20s，零失败
- 两轮修复：①装齐格式测试依赖（xlrd/odfpy/xlwt/tabulate/openpyxl，
  含 pbr 修复）；②剩余 1 个时间戳日期断言失败为沙箱时区 CST 非 UTC
  ——TZ=UTC 重跑全过（环境差异，非库缺陷，rule 5.2 如实记录）
- 适配后：test_package R34 真实 import 打包的 tablib，Dataset + CSV
  导出校验，1/1 = 100%

## 已知限制
- 核心包仅含格式骨架（csv/json/yaml 等原生格式），xlsx/dbf 等需可选
  extras 依赖才可用——本次仅适配核心包
