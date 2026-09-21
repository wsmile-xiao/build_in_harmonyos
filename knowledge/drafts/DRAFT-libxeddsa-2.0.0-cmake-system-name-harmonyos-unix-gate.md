# OHOS 适配版 CMakeToolchain 的 CMAKE_SYSTEM_NAME=HarmonyOS 映射让上游 if(UNIX) 平台分派落空

- **草稿 ID**: DRAFT-libxeddsa-2.0.0-cmake-system-name-harmonyos-unix-gate
- **来源**: libxeddsa 2.0.0-20231128.d725c81 适配（ref10 与 FindSodium 两处 `if(UNIX)`，覆盖为 Linux 后真机一次通过）
- **分类**: build / cmake / ohos / platform / toolchain
- **状态**: 本地草稿（路径 B 知识库扩展申请中）
- **严重级**: 2（configure 阶段 FATAL_ERROR，报错位置离根因远）

## 问题 / 错误签名

- OHOS 适配版 conan（私有 PyPI，基线 2.29.1）+ `ci/conan/profiles/ohos-aarch64`
  下 `cmake.configure()`，报：
  - `Unsupported operating system (neither UNIX nor Windows). CMake will exit.`，或
  - `System is unknown to this CMake` / `CMAKE_C_COMPILER ... not working`（try_compile 探测）。
- 上游 CMake 常见写法 `if (UNIX) ... elseif (WIN32) ... else() FATAL_ERROR`。

## 根因

适配版 CMakeToolchain 把 `os=OHOS` 自动写成 `CMAKE_SYSTEM_NAME=HarmonyOS`
（profile 头部注释明示，Meson/Qbs 同理映射 harmonyos）。设备上的 vanilla
CMake（实测 4.1.2 与 4.4.3）**没有 Platform/HarmonyOS.cmake**，因此
`UNIX`、`WIN32` 全为 FALSE——所有平台分派走进 else 分支。

真机构建是 native（同 profile 作 `-pr:h`/`-pr:b`，clang 目标
aarch64-linux-ohos），把系统名声明为 **Linux** 完全成立：musl 头文件、
`CHECK_SYMBOL_EXISTS` 符号探测（libxeddsa 的 getentropy 探测命中 musl
unistd.h）、链接、运行全部按 Linux 语义工作。

## 最小修复（真机验证）

```python
# generate() 里，et/7.0.0 合入先例
tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
```

libxeddsa 实测：ref10/CMakeLists.txt（随机源探测 + 全部目标）与
FindSodium.cmake（UNIX 分支查找）两处 `if(UNIX)` 一次走通，frp 真机
conan create 全绿（ctest 3/3 + test_package 全过）。

## 影响面与推广

- 识别：错误文本 `Unsupported operating system` / `System is unknown to
  this CMake` 在 configure 早期出现、且上游有 `if(UNIX)` 分派，基本即此条。
- test_package 同样受影响：小库可走 direct-cc（`${CC} ${CFLAGS}` + conanbuild
  环境）完全绕开 CMake（libsodium 1.0.20 / libmacaroons 0.3.0 先例）；
  大库照旧 CMake + 本条覆盖。
- 机制口径：工具链把目标平台写成下游工具不认识的名字时，以"目标 ABI 事实"
  为准显式声明——OHOS 用户态就是 Linux ABI + musl。
- 这是 et/7.0.0（已合入）之后又一次独立复现，本条补全了机制解释与
  平台模块缺失的直接证据。
