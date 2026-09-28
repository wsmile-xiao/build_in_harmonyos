# DRAFT-fyba-4.1.1-header-platform-macro-defines：公开头平台宏条件类型定义需要 cpp_info.defines 导出

> Contributor: pc4-4 | Status: Draft | Updated: 2026-09-27
> Source: fyba 4.1.1 适配 HarmonyOS PC（task fyba-4.1.1-r01-pc4-4）
> 对应：`knowledge/drafts/DRAFT-fyba-4.1.1-header-platform-macro-defines.kv`

## 现象

库本体用 conan create 构建成功，但消费者（test_package）include 安装后的公开头时报类型未定义：

```console
test.cpp:22:5: error: unknown type name 'UT_INT64'
    UT_INT64 sluttpos = 0;
    ^
```

再往上看，`fyut.h`（公开头）里同一类型在多个函数原型中也是 `unknown type name`。

## 根因

老式（1990s-2000s）C/C++ 库的公开头习惯用平台宏做条件编译。fyba 的 `fyut.h`：

```c
#ifdef LINUX /* specifically the LINUX */
#  include <stdint.h>
#  include <inttypes.h>
#  define UT_INT64 int64_t
#endif
```

`UT_INT64` **只在 `#ifdef LINUX` 分支里定义**。库本体编译时，上游 Makefile.am 的
`AM_CPPFLAGS` 硬编码了 `-DUNIX -DLINUX`，所以库自身构建全程有 `LINUX` 宏、一切正常；
但消费者只 include 安装后的公开头，没有人给它传 `-DLINUX`——`UT_INT64` 在消费者眼里
从未被定义，于是编译报 unknown type name（库编译期带上的宏约定不会自动传递给消费者）。

## 方案（按侵入性从低到高）

1. **配方导出 cpp_info.defines（推荐，零源码侵入）**：在 `package_info()` 里把与库编译
   一致的平台宏明示导出，消费者经 Conan 传递依赖自动获得：

   ```python
   def package_info(self):
       ...
       # fyut.h 仅在 #ifdef LINUX 下定义 UT_INT64；库以 -DUNIX -DLINUX 编译
       self.cpp_info.defines = ["UNIX", "LINUX"]
   ```

   实测 fyba 消费者 test.cpp/test_ohos.cpp 编译运行全绿（ctest 2/2）。
2. 补丁在公开头条件分支外加无条件回退定义（`#ifndef UT_INT64 #define ... #endif`），
   仅当平台宏语义不宜外泄时使用。

## 验证

```bash
conan create archives/f/fyba/4.1.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 期望：test_package 两个消费者用例编译运行通过，无 'unknown type name UT_INT64'
```

## 适用边界 / 反例

- **适用**：公开头用 `#ifdef LINUX/UNIX/WIN32` 等平台宏条件定义类型/常量、库本体以相同
  宏编译的库；凡消费者 include 公开头即命中。
- **反例**：库本体也没用这些宏（条件分支不生效）时不适用；宏仅在内部头/私有头时不需要导出；
  不应把 `-DLINUX` 硬编码进上游 Makefile.am（R8：补丁禁平台宏，且治标不治本——消费者
  include 公开头仍无宏）。