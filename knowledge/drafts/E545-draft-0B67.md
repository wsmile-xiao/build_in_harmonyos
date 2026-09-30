# E545 — 原生 OHOS 构建的 `System is unknown to cmake` 只是告警，不需要 `CMAKE_SYSTEM_NAME` 覆盖

## 错误特征

configure 阶段反复刷出（每次编译器探测/头文件探测都会重复一次）：

```
System is unknown to cmake, create:
Platform/HarmonyOS to use this system, please post your config file on discourse.cmake.org so it can be added to cmake
```

随后 configure / 编译 / 运行**全部成功**。

## 触发条件

- 构建系统: cmake 3.x / 4.x
- 平台: OHOS / OpenHarmony（`uname -s` 返回 `HarmonyOS`）
- 关键前提: **原生构建**，即 `build == host == OHOS`（conan 用同一份 profile 作 `-pr:h` 与 `-pr:b`，`conan_toolchain.cmake` 的 `generic_system` 块为空）

## 根因分析

OHOS 上 `uname -s` 返回 `HarmonyOS`，cmake 的 `CMakeDetermineSystem` 与已知系统表（Linux / Darwin / Android / …）不匹配，于是回落成 `CMAKE_SYSTEM_NAME=HarmonyOS` 并尝试 `include(Platform/HarmonyOS.cmake)`；该文件不存在时只打印上述告警。

在**原生**构建下这只是缺少 `Platform/<name>.cmake` 的告警——后续探测仍按默认 Unix 平台变量完成，实测 `CMAKE_SYSTEM_NAME` / `CMAKE_HOST_SYSTEM_NAME` 均为 `HarmonyOS`，程序正常编译并运行。

**与 E092 的关系**：E092 的处方 `-DCMAKE_SYSTEM_NAME=Linux` 面向的是 conan CMakeToolchain 在**交叉**场景把 `os=OHOS` 映射成 cmake 不认的系统名、导致 `conan_toolchain` 整体不可用的情形。本条目是其适用边界：原生构建下不需要也不应覆盖（P001：鸿蒙是原生编译环境，不是交叉编译）。

**判据**：`conan_toolchain.cmake` 的 `generic_system` 块为空 + `uname -s` = `HarmonyOS` → 告警可忽略。

## 解决方案

### 推荐方案

判定为原生构建时**按告警放过**，不设 `CMAKE_SYSTEM_NAME`。

```bash
grep -n "generic_system" conan_toolchain.cmake   # 空块 => 原生，告警可忽略
```

### 备选

若某些上游模块确实依赖 `Platform/<name>.cmake` 提供的变量（如 `CMAKE_DL_LIBS`、共享库后缀），可补一个**最小**的 `Platform/HarmonyOS.cmake` 只设置缺失变量，而不是改成 Linux。

### 禁止做法

- ❌ 在原生 OHOS 构建上设 `CMAKE_SYSTEM_NAME=Linux`：引入交叉编译语义（可能跳过 run-time 探测、切到 Linux 平台模块假设），掩盖真实平台差异。

## 验证

```bash
cmake -S . -B build && cmake --build build && ./build/<target>
uname -s                                     # HarmonyOS
grep -n "generic_system" build/conan_toolchain.cmake   # 空块
```

## 关联条目

- 相似: E092（交叉场景的同一告警签名，处方不同）、E550（多后端图像库交叉适配组合方案，其中记录了 ML-0035）
- 原则: P001（鸿蒙是原生编译环境，不是交叉编译）
- 实证: libosmscout 2024.06.02.1（configure 期反复告警，上游 69/69 测试全绿，消费者 39/39 全绿）
