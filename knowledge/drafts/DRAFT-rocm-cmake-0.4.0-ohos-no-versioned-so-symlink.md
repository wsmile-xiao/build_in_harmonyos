# DRAFT-rocm-cmake-0.4.0-ohos-no-versioned-so-symlink

> 状态：草稿（来自 rocm-cmake 0.4.0 适配，上游 tag rocm-4.2.0）
> 类别：cmake / shared-library / ohos-platform / upstream-test

## 现象

rocm-cmake 0.4.0 上游测试套件（`test/test.cmake` 驱动 `test/pass/*.cmake` 17 个 +
`test/fail/*.cmake` 2 个 = 19 个 ctest 用例）在 HarmonyOS PC 上实测 **15 通过 / 4 失败**。
其中两个失败用例：

- `pass-simple-soversion`
- `pass-simple-soversion-env`

二者构建一个带 `SOVERSION` 的普通 CMake 共享库并断言版本化软链 `libsimple.so.1` 存在；
在 OHOS 上该文件缺失，断言失败。

## 根因

OHOS 平台不生成共享库的 `.so` 版本化符号链接链（`libX.so -> libX.so.MAJOR ->
libX.so.MAJOR.MINOR.PATCH` 中 `libX.so.MAJOR` 环节缺失）。

对照实验：一个普通 CMake 工程（`add_library(foo SHARED)` +
`set_target_properties(foo PROPERTIES VERSION x.y.z SOVERSION n)`）在 OHOS 上同样**不产**
版本化软链，证明这是平台/工具链能力差异，而非 rocm-cmake 配方缺陷。同类结论在已合入的
rocm-cmake 0.12.0 归档中亦被记录（其 `manifest.yaml` 的 `test_failures` 明确写
"HarmonyOS no .so.1 symlinks"，`pass-simple-soversion` / `pass-simple-soversion-env`
两条同因豁免）。

## 方案

平台能力差异导致的上游用例失败，**禁止修改上游测试文件、禁止 stub 伪造通过**：

1. 配方 `build()` 末尾仍执行整条上游 ctest 套件（TEST_QUALITY_SPEC §3.1 层 1），
   用 `ctest -E` **显式**排除 4 个平台受限用例：

   ```
   ctest --output-on-failure -E 'pass-simple-soversion|pass-simple-soversion-env|pass-version-norepo|pass-version-parent'
   ```

2. 在 `test_package/MANIFEST.yml` 的 `excluded_tests` 与 `notes.md` 中**逐条声明豁免 +
   根因**（TEST_QUALITY_SPEC §3.3 路径 3）。

> 若某生产库确实需要版本化 SONAME/软链，可在配方 `generate()` 走
> `CMAKE_PLATFORM_NO_VERSIONED_SONAME` + `CMAKE_SHARED_LIBRARY_SONAME_*_FLAG` 方案
> （参见 E330/E331）。rocm-cmake 本身不产共享库，无需该修复。

## 适用边界

- 适用：在 OHOS 上断言共享库版本化软链（`.so.MAJOR` / `.so.VERSION`）存在的上游测试
  或消费者脚本。
- 不适用：仅断言未版本化 `libX.so` 存在的用例；这类在 OHOS 上正常通过。

## 与已有条目的差异

- E331 面向 CMake `VERSION`/`SOVERSION` 共享库软链环节在 HMDFS 上 "Operation not
  permitted" 的**构建失败**；本条面向上游**测试断言**因版本化软链缺失而失败、以显式
  `ctest -E` 豁免的处置策略。
- E330/E383 面向"OHOS 无 CMake 平台模块导致 SONAME flag 为空"；本条不涉及 SONAME
  flag 缺失，聚焦版本化软链的文件层面缺失。

## 关联交付

- `archives/r/rocm-cmake/0.4.0/`（conanfile.py、test_package/MANIFEST.yml、notes.md）
