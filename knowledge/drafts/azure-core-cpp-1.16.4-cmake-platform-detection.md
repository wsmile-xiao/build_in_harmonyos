# DRAFT-azure-core-cpp-1.16.4-cmake-platform-detection：上游 CMake 平台三分支检测对 HarmonyOS 落入 else() FATAL

> Contributor: azure-core-cpp-1.16.4 适配 | Status: Draft | Updated: 2026-08-22
> Source: archives/a/azure-core-cpp/1.16.4

## 现象

azure-core-cpp 1.16.4 在 OHOS armv8 工具链（clang15, libc++, C++17, Release）下执行 `conan create`，CMake configure 阶段报错：

```
CMake Error at cmake-modules/AzureTransportAdapters.cmake:73 (message):
  Unsupported platform.
```

配置阶段直接终止，尚未进入编译。该错误来自 azure-sdk-for-cpp 的
`cmake-modules/AzureTransportAdapters.cmake` 中的平台三分支判定：

```cmake
if (WIN32 OR MINGW OR MSYS OR CYGWIN)
  # Windows 分支（WinHTTP / libcurl 传输适配）
elseif (UNIX)
  # POSIX 分支（libcurl 传输适配）
else()
  message(FATAL_ERROR "Unsupported platform.")
endif()
```

## 根因

OHOS 工具链（本仓库 `ohos-aarch64` profile）使 CMake 将 `CMAKE_SYSTEM_NAME` 设为 `HarmonyOS`。
`HarmonyOS` 既不匹配 `WIN32`，也不匹配 `UNIX`，于是落入 `else()` 分支直接 FATAL。
AzureTransportAdapters.cmake 的职责是挑选 HTTP 传输适配器（最新版默认选 libcurl），
HarmonyOS 是 POSIX 语义平台（ELF、pthread、libc++），本应走 libcurl 分支。

关联根因：OHOS 适配版 Conan 的 CMakeToolchain 自动将 `os=OHOS` 映射为
`CMAKE_SYSTEM_NAME=HarmonyOS`（见 ci/conan/profiles/ohos-aarch64 注释），
这是正确行为，问题只在上游三分支判定未覆盖该平台名。

## 边界（OHOS 特有）

- Linux/Android 已有对应平台路径，不触犯此分支；仅 HarmonyOS（CMAKE_SYSTEM_NAME=HarmonyOS）命中。
- 同类检测（`CMAKE_SYSTEM_NAME` 精确比较 vs 全局变量 `WIN32/UNIX`）在
  gtk4/pango 等依赖链中可能以不同措辞出现，但修复思路一致：把 HarmonyOS 归入 UNIX/POSIX 分支。

## 方案（最小修复）

以 patch 形式修改该 cmake-modules，将 `elseif (UNIX)` 扩展为：

```cmake
elseif (UNIX OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")
```

- patch 文件：`archives/a/azure-core-cpp/1.16.4/patches/0001-add-harmonyos-platform-support.patch`
- 未改动上游源码管理，通过 conandata.yml `patches` 段应用（带 patch_description/patch_type）。

## 验证方式

```bash
TMPDIR="$HOME/tmp" CC=clang CXX=clang++ \
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing \
  -o "&:shared=True" -o "&:build_transport_curl=True" \
  -c "tools.build:compiler_executables=..."
```

- 修前：`Unsupported platform` 配置失败（首次失败证据，退出码 1）。
- 修后：配置通过 → 编译生成 `libazure-core.so` → test_package 编译链接运行 1/1 通过。
- 上游安全离线测试 140/140 通过（gtest 1.17.0，TMPDIR patch 后）。

## 查重结论（b_evidence_search）

- Git 历史/全部分支：零命中 azure-core-cpp。
- knowledge/drafts/、knowledge/graph/：无等价条目。
  - E265-draft-2301「Select Windows positively and unknown systems by concrete POSIX capability」
    是 autotools 正向能力探测思路，针对 autotools 平台探测，非 CMake 三分支模式，不适用。
  - E322-draft-F2BA 是 HarmonyOS 下缺少 Platform/HarmonyOS.cmake 导致 SONAME 缺失，
    现象不同（链接期 soname），非 configure 期平台三分支判定，不适用。
- 关联复用：codeload 无扩展名 URL 的 get() BadZipFile 问题已由
  `knowledge/drafts/E321-conan-get-url-no-extension-badzipfile.kv` 覆盖，本次仅复用
  （conanfile.py 中 `get(..., filename="azure-core_1.16.4.tar.gz")` 按 E321 建议实施），不重复创建。

## 新增/扩展内容

该项为新增知识：上游 CMake 平台三分支（WIN32/UNIX/else）在 HarmonyOS 下落入 else() FATAL 的
检测模式与最小修复，配 patch 示例与验证证据；无等价条目，故创建本成对草稿（.kv + .md）。