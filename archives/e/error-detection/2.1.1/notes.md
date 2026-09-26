# error-detection 2.1.1 适配笔记

## 编译环境
- 构建系统: cmake（上游无构建系统，配方注入 CMakeLists.txt）
- 编译日期: 2026-09-26
- 编译器: clang 15.0.4 (/data/service/hnp/bin/clang)
- 状态: built

## 官方来源
- 上游: https://github.com/aKaReZa75/Error_Detection
- 上游无 tags / releases / 版本声明；任务声明版本 2.1.1，源固定到官方 main HEAD
  commit df775354e86caedf4b0a40e88a6332887238feda（codeload 官方 HTTPS 源）。
- 源码 SHA-256: e673163a38a0bdf139e66e55484ea96ee1ff50bf3fc37c272cde3179a261923b
- 源码内容: Sources/err.c + Sources/err.h（纯 C，GPL-3.0）+ 文档 + 图片。

## 依赖分析
- 无第三方编译依赖。
- err.h 包含外部 "aKaReZa.h"（作者框架头，不在本仓库；AVR 变体仅 AVR）。
  err.c 只使用其中的 bitCheck / bitChange / bitCheckHigh / bitShiftLeft 位宏与
  uint8/16/32_t、bool 类型，且与作者 STM32 变体（通用版）定义一致。

## 适配方案
1. 补丁 0001-err-h-inline-bit-macros.patch：用 `<stdint.h>` + `<stdbool.h>` +
   所需的位宏（bitSet/bitClear/bitToggle/bitCheck/bitChange/bitCheckHigh/
   bitCheckLow/bitShiftLeft/bitShiftRight）内联替换 `#include "aKaReZa.h"`，
   消除对仓库外 AVR 专用框架头的依赖（portability）。
2. conanfile.py 在 source() 注入最小 CMakeLists.txt：C99 静态库
   `error-detection`（Sources/err.c），PUBLIC_HEADER=Sources/err.h，
   install 导出 error-detectionTargets.cmake + error-detection::error-detection。
3. test_package：消费者测试 test.c 以 "123456789" 标准 CRC 校验向量覆盖全部
   6 个公开 API（checkSum8/16/32_Calc、CRC8/16/32_Calc），断言：
   checkSum8=0xCF、checkSum16=0x0CF9、checkSum32=0x0CF9、CRC-8/MAXIM=0xA1、
   CRC-16/CCITT-FALSE=0x29B1、CRC-32/IEEE=0xCBF43926。

## 验证结果
- conan create（ohos-aarch64 profile，os=OHOS / clang 15 / armv8）编译通过，
  test_package 6 项断言全部 PASS。

## 上游测试
- 上游未提供测试套件（无 test/、无测试源、无样例、无基准、无 fixture），
  上游用例总数 = 0；以 test_package 消费者测试作为契约验证。
---

**编译结束**: 2026-09-26 02:01
**最终状态**: built
