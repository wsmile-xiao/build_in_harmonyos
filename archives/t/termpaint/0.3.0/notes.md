# termpaint 0.3.0 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-09-08
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: built

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | termpaint_input.c strict-prototypes error | Clang 15 treats `()` as deprecated | Add `void` to function definitions |
| 2 | ttyrescue-fexec-blob defaults to true, Linux only | meson.build checks host_system == 'linux' | Pass -Dttyrescue-fexec-blob=false |
| 3 | testtermpaint link fails: u8p<char*> undefined | C++17 std::string::data() returns char* for non-const | conanfile.py builds only library targets |
| 4 | Meson cannot find llvm-ar | PATH not set | Export PATH with /data/service/hnp/bin |

## 依赖版本
无外部 Conan 依赖。所有第三方库均内嵌源码树。

## 验证结果
1/1 termpaint:testtermpaint OK (133 test cases, 21668873 assertions)
