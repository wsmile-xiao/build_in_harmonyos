# boost1.84-program_options 1.84.0 适配笔记

## 形态决策：方案 A（独立裁剪编译）

- **方案 A（采用）**：从 boost 1.84.0 官方源码裁剪，手动 clang++ 编译 `libs/program_options/src` 全部 11 个翻译单元为 `libboost_program_options.a`（winmain.cpp 是上游 CMakeLists 在所有平台编译的空翻译单元，保留以对齐上游）。
- **方案 B（否决）**：requires boost/1.84.0 元包——虽然元包编译了 program_options，但组件拆分任务要求独立包形态（与 boost1.84-url/date_time 等系列拆分包对齐）；且元包与组件包同用 cmake_file_name "Boost" 时，同工程 CMakeDeps 生成文件互相覆盖会冲突。本包 cmake_file_name 用 "boost1.84-program_options" 避免共存冲突。

## 编译方式

b2 在 OHOS 不兼容（E068）。手动 clang++：
- 参数：`-std=c++17 -stdlib=libc++ -fPIC -O2 -DNDEBUG -DBOOST_ALL_NO_LIB -DBOOST_SP_NO_PTHREAD_SETCANCELSTATE`
- 补丁：复用元包 0001（sp_thread_sleep.hpp，特性宏 R8 合规）
- 源文件集合与上游 `libs/program_options/build/Jamfile.v2` 的 SOURCES 一致

## 上游测试

13 个测试全部通过（minitest.hpp 纯 assert 框架，不依赖 boost.test 库）：cmdline_test、options_description_test、variable_map_test、positional_options_test、split_test、exception_test、exception_txt_test、optional_test、quick（--path=initial）、unrecognized_test、required_test（required_test.cfg）、parsers_test（config_test.cfg）、unicode_test（ucs2.txt/utf8.txt）。

带参数的测试按上游 B2 测试框架行为传入对应数据文件（与元包 archives/b/boost/1.84.0 的上游测试段一致）。

## test_package 运行方案

OHOS 原生执行采用**签名+LD_LIBRARY_PATH** 流派（boost 1.90.0.2.1/1.85.0 先例）：
- `clang++ -print-file-name=libc++_shared.so` 编译器内省定位 SDK 运行库目录（无硬编码 SDK 版本）
- `llvm-objcopy --remove-section .codesign` + `binary-sign-tool -selfSign 1` 签名
- LD_LIBRARY_PATH 指向 libc++_shared.so 目录后运行
- 上游派生断言 31 checks 全过

## 依赖

无 conan 依赖。

## 验证命令

```
conan create . --user=ohpcd --channel=stable -pr:h=~/.conan2/profiles/ohos-aarch64 -pr:b=~/.conan2/profiles/ohos-aarch64 --build=missing
```
---

**编译结束**: 2026-09-05 18:38
**最终状态**: published
