# stc 5.0 适配笔记

## 编译环境
- 构建系统: makefile（上游纯 Makefile，无 configure；另有 meson.build 未采用）
- 编译日期: 2026-09-08
- 编译器: clang 15.0.4（OHOS 工具链 /data/service/hnp/bin/clang）
- 状态: built

## 编译步骤

1. 源码: 官方 tag v5.0（commit 0ccf9c3d6e114d99fc698a0200b7ecec995d5ad2）
   tar.gz SHA-256: d61353852b9d7ef69b56fa32edcbc7934f2153385f3778536234201ceebcc950
2. `make lib CC=clang CFLAGS='-std=c11 -Iinclude -MMD -O3 -Wpedantic -Wall -Wextra -Werror -Wno-missing-field-initializers -fPIC' BUILDDIR=bld`
   产物: `bld/libstc.a`（9 个对象: cstr_core cstr_io cstr_utf8 cregex csview cspan fmt random stc_core）
3. 上游测试: `make all`（含 test_all）后运行 `./bld_HarmonyOS/clang/tests/test_all` → 33/33 通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | make 编译测试报 `'stc/cstr.h' file not found` | 环境预置 `CFLAGS=-fPIC -O2` 覆盖了 Makefile 的 `CFLAGS ?=` 默认值，`-Iinclude` 丢失 | 命令行显式传完整 CFLAGS（含 -Iinclude）；conanfile.py 的 build() 同样显式传 CFLAGS |
| 2 | `make: jobserver mkfifo ... Operation not permitted` | 环境不支持 make jobserver fifo | 环境噪音，`make lib` 单目标不受影响；已忽略 |

## 依赖版本

无第三方依赖（仅标准 C 库 + -lm，OHOS musl 自带）。

## 验证结果

- 上游测试: `tests/*_test.c` 共 8 个测试文件 + `tests/main.c` → `test_all`，33 个用例全部通过（33 ok, 0 failed, 0 skipped），运行 5.5ms
- conan-verify: G0-G4/L2/L4/L5 门禁结果见 reports/ 验证报告

## 交付物

| 文件 | 说明 |
|------|------|
| include/stc/*.h + include/c11/fmt.h | 头文件（C11 模板容器库主体） |
| lib/libstc.a | 静态归档（cstr_io/cstr_utf8/cregex/fmt/random/cspan 等非头文件实现） |

## 注意事项

- STC 主体是头文件库；IO/utf8/正则/格式化等实现需链接 libstc.a
- 消费者需 C11（头文件）与 `-lm`（静态库符号）
- codeload URL 以 tag 名结尾无 `.tar.gz` 后缀，conandata.yml 必须带 `filename` 字段（否则 conan get 误判 zip 格式，见 abcmidi 先例）
---

**编译结束**: 2026-09-08 01:26
**最终状态**: built
