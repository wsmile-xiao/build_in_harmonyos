# E543 — 上游 CMake 仅 Linux 分支链接 Threads::Threads 时，OHOS 配方需补 pthread system_libs

> 草稿（draft）。来源任务：zycore-c/1.5.1 适配（HarmonyOS PC aarch64，pc3-6 R01），2026-09-18。

## 错误特征

```
undefined reference to pthread_key_create
>>> referenced by Thread.c.obj
ld.lld: error: undefined reference to pthread_*
```

库本身可正常编译（.a/.so 生成无链接错误），错误只在下游**静态链接消费者**链接时暴露。

## 触发条件

- 构建系统: CMake
- 阶段: linking（根因在 configure 的条件链接分支）
- 前置:
  1. 上游用 `if (${CMAKE_SYSTEM_NAME} STREQUAL "Linux")` 精确匹配后才
     `find_package(Threads REQUIRED)` 并链接 `Threads::Threads`；
  2. 库源码实际调用 pthread API（如 `pthread_key_create`、`pthread_mutex_*`）；
  3. OHOS 上 `CMAKE_SYSTEM_NAME=HarmonyOS`，该分支整体不执行；
  4. 配方以静态库交付。

zycore-c 1.5.1 实例（`CMakeLists.txt:193-197`）：

```cmake
if (${CMAKE_SYSTEM_NAME} STREQUAL "Linux" AND NOT ZYAN_NO_LIBC)
    target_compile_definitions("Zycore" PRIVATE "_GNU_SOURCE")
    set(THREADS_PREFER_PTHREAD_FLAG ON)
    find_package(Threads REQUIRED)
    target_link_libraries("Zycore" Threads::Threads)
endif ()
```

OHOS 下分支不命中，`libZycore.a` 无 pthread 链接信息；而
`src/API/Thread.c` 的 `ZyanThreadTlsAlloc` 调用 `pthread_key_create` 等符号，
下游消费者（如本任务 `test_zycore_ohos` 调用 `ZyanThreadTlsAlloc`）链接时
若配方未透传 pthread 依赖即失败。

## 与既有条目关系

- 与 **E607**（草稿，osqp）同家族：都是"上游 CMake 平台分支只判
  Linux/Darwin/Windows，OHOS 下分支不生效"。但 E607 缺的是**平台源文件被
  漏编**（编译期/链接期 undefined symbol 指向未编译的 .c 实现），修复面在
  源码/补丁层；本条目缺的是**链接库依赖**（Threads::Threads 未链接），库
  所有源文件都编了，修复面在 Conan 配方 `package_info` 层，不产生源码补丁。
- 与 **E003** 相关：E003 面向编译/链接期缺 -pthread 标志（add-cflags）；
  本条目面向配方声明 `system_libs` 供下游静态消费者传递链接，二者互补。

## 推荐方案

在 Conan 配方 `package_info()` 中，对 `os in ("Linux", "OHOS")` 声明
`cpp_info.system_libs = ["pthread"]`：

```python
def package_info(self):
    self.cpp_info.libs = ["Zycore"]
    ...
    if self.settings.os in ("Linux", "OHOS"):
        self.cpp_info.system_libs = ["pthread"]
```

原理：CMakeDeps 为 `Zycore::Zycore` 目标生成带 pthread 传递依赖的配置，
下游消费者无需手工加 `-pthread`，静态链接自动闭环。

## 验证

```bash
conan create . --user=ohpcd --channel=stable \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 消费者 test_package 中直接链接 Zycore::Zycore 并调用 Thread API：
#   zycore-c ohos test passed   (Thread TLS/String/Vector 三组断言全过)
```

实测（zycore-c 1.5.1）：`conan create` exit 0，`test_zycore_ohos` 调用
`ZyanThreadTlsAlloc/SetValue/GetValue` 与 `ZyanThreadGetCurrentThreadId`
实际运行输出 `zycore-c ohos test passed`——证明 pthread 依赖已由配方
`system_libs` 正确传递到下游链接与运行。

## 禁止做法

- ❌ 在 patches 中加 `#ifdef __OHOS__` 或 `-lpthread` 平台宏分支（R8/PF5 拦截）；
- ❌ 忽略 `undefined reference to pthread_*` 链接错误（必须由配方声明闭环）；
- ❌ 把本问题写成当前库自身缺陷（实为上游平台分支覆盖不足 + 配方声明缺口）。

## 适用边界 / 反例

- 适用于：上游以 `CMAKE_SYSTEM_NAME STREQUAL "Linux"` 条件链接 Threads、
  源码使用 pthread API、静态交付的 CMake 库（zycore-c、zydis 家族等）。
- 反例：上游无条件 `find_package(Threads)` 或在其他分支也链接 Threads 的库
  不受影响；共享库交付时动态链接器在运行时解析，无此编译期链接缺口。
