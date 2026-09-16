# DRAFT-dwarves-ohos-cmake-soname-flag — OHOS 无 CMake 平台模块导致 SOVERSION 不产出 DT_SONAME，需显式注入 soname 链接 flag

> **Contributor**: pc1-26 | **Status**: DRAFT | **Updated**: 2026-09-10
> **Severity**: blocking (2) | **Category**: conan / cmake / linking / ohos
> **Audience**: 在 OHOS 上用 CMake SOVERSION 构建共享库的 Conan 2 library 配方作者

## 触发（trigger）

dwarves 1.30 OHOS PC aarch64 适配：上游 CMakeLists 对
`libdwarves/libdwarves_emit/libdwarves_reorganize` 设置
`PROPERTIES VERSION 1.0.0 SOVERSION 1`，W3 门禁 L5a 报：
`libdwarves.so 缺少 DT_SONAME — 下游链接器无法按 SONAME 寻址`。

## 症状（symptom）

W3 L5 基线检查：
```
[fail] L5a: libdwarves.so 缺少 DT_SONAME — 下游链接器无法按 SONAME 寻址
[fail] L5a: libdwarves_emit.so 缺少 DT_SONAME ...
[fail] L5a: libdwarves_reorganize.so 缺少 DT_SONAME ...
```

`llvm-readelf -d libdwarves.so` 只有 NEEDED，无 SONAME 条目；
包内也无 `.so.1` / `.so.1.0.0` 符号链接。

## 根因（root cause）

OHOS 无 CMake 平台模块（configure 输出 `System is unknown to cmake, create:
Platform/HarmonyOS`），CMake 因此未定义
`CMAKE_SHARED_LIBRARY_SONAME_C_FLAG`（Linux 平台上为 `-Wl,-soname,`）。
SOVERSION 属性虽声明，但链接命令缺少 soname flag，产出无 DT_SONAME
的 `.so`（无版本化符号链接），下游链接器无法按 SONAME 寻址。
与打包期问题（E274 缺 symlink、E316 缺 SONAME 实体）不同，本候选是
**构建期 flag 未注入**，属 OHOS CMake 平台能力缺口。

## 方案（approach）

在配方 generate() 中显式补上 soname flag：

```python
tc = CMakeToolchain(self)
# OHOS 无 CMake 平台模块, CMAKE_SHARED_LIBRARY_SONAME_C_FLAG 未定义
tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
tc.generate()
```

## 验证（verification）

```
conan create archives/d/dwarves/1.30 -pr:h=<repo>/ci/conan/profiles/ohos-aarch64 \
  -pr:b=<repo>/ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
```
修复后包内出现 `libdwarves.so.1`、`libdwarves.so.1.0.0` 符号链接；
`llvm-readelf -d` 显示 `(SONAME) Library soname: [libdwarves.so.1]`；
W3 L5a 门禁 pass（`L5_RESULT=pass: bin/ has content`）。

## 适用边界（boundary）与反例

- 适用：OHOS（及任何缺 CMake 平台模块的系统）上用 CMake SOVERSION 的共享库
- 反例：Linux/glibc 平台 CMake 自带平台模块，无需注入；静态库无关；
  打包期 SONAME 实体/符号链接缺失（E274/E316）属另一阶段问题
- 查重关联：E274（create-soname-symlink）、E316（copy-soname-entity）覆盖打包期；
  本候选是构建期 flag 注入，边界新颖

## 关系字段

- similar_to: E274, E316
- caused_by: ohos-cmake-no-platform-module
- prerequisite_of: W3 L5a 门禁（共享库 DT_SONAME 质量门禁）
- conflicts_with: 无