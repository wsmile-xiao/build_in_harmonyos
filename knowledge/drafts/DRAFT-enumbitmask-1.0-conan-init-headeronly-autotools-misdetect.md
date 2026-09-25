# DRAFT: conan-init 将无构建系统单头库误判为 autotools，生成错误配方类型

> 草稿状态：待审核。来源：enumbitmask 1.0 适配（R01, pc4-23）。
> 对应 .kv：`knowledge/drafts/DRAFT-enumbitmask-1.0-conan-init-headeronly-autotools-misdetect.kv`

## 问题描述

对无构建系统的 header-only 单头 C++ 库执行标准流程：

```bash
python3 scripts/ohc-run.py init-build enumbitmask 1.0 --url=https://github.com/Reputeless/EnumBitmask/archive/refs/tags/v1.0.tar.gz
python3 scripts/ohc-run.py conan-init enumbitmask 1.0
python3 scripts/ohc-run.py conan-verify enumbitmask 1.0 --profile ohos-aarch64
```

`init-build` 将 `build_system` 判为 `autotools` → `conan-init` 按 autotools 模板
生成 `conanfile.py`（`AutotoolsToolchain` + `autotools.configure()/make()`）→
`conan-verify` G2 `conan create` 失败：报 `Invalid: 'settings.os.version' value not defined`
（test_package 阶段）或找不到 `configure`。

## 根因

`scripts/ohc/init_build.py::_guess_build_system(url)` 是启发式判断：URL 不含
`cmake.org`/`mesonbuild`/`openssl`/`python` 特征、软件又不在
`scripts/software-registry.yaml` 时，**兜底返回 `"autotools"`**。无构建文件
（无 configure/CMakeLists.txt/Makefile/meson.build）的纯头文件库被判为 autotools，
配方类型错误 → G2 必然失败。

## 影响范围

- 无构建系统、仅分发头文件的 header-only C++ 库
- init-build → conan-init → conan-verify 全流程
- 受影响阶段：配方生成（conan-init）与构建验证（G2）

## 修复方案

1. 以 `build_system="headeronly"` 重建档案（或直接修正 manifest 的
   `build.system: headeronly`）。
2. 按 `templates/conanfile-headeronly.py.tmpl` 重写 `conanfile.py`：
   - `package_type = "header-library"`
   - 不定义编译型 `build()`（header-only 无编译步骤；不得伪造编译日志，R34）
   - `package()` 用 `conan.tools.files.copy` 拷贝头文件与 LICENSE 到
     `include/` 与 `licenses/`
   - `package_id()` 中 `self.info.clear()`
   - `package_info()` 中 `cpp_info.bindirs = []`、`cpp_info.libdirs = []`
3. `conandata.yml` 保留官方 HTTPS 源 + 实测 SHA-256。
4. `test_package` 必须为真实消费者用例（R34）：include 公开头并使用公开宏/API
   编译运行（如 `DEFINE_BITMASK_OPERATORS` + 位运算断言），禁止空壳 printf。

## 参考实现

`archives/e/enumbitmask/1.0/`：
- `conanfile.py`（headeronly 配方）
- `conandata.yml`（官方源 + SHA-256 `233efdef...13d`）
- `test_package/test.cpp`（消费者用例）
- `test_package/test_ohos.cpp`（鸿蒙专项）
- `reports/conan-verify-report.md`（G1-G5 全 PASS）
- `reports/test-report.md` / `reports/upstream-test-ledger.md`

## 验证

- `conan-verify`：G1/G2/G3/G4 PASS，L2/L4/L5 完成
- conan create 内 ctest：2/2 PASS（test_enumbitmask + test_ohos_enumbitmask）
- W3 本地 CI 模拟（build_and_test.sh）：PASS

## 适用边界 / 反例

- **适用**：源码仅含头文件（.h/.hpp）且无任何构建脚本的库。
- **不适用**：有 CMakeList.txt/Makefile/configure/meson.build 的库（此时 autotools
  或 cmake 判读是合理的，属另一类问题）；有构建文件但被忽略的"多语言仓库"
  （此时是嵌套源码提升问题，见 fastnoiselite 知识）。