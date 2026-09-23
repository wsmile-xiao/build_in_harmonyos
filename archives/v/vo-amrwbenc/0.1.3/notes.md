# vo-amrwbenc 0.1.3 适配笔记

## 编译环境
- 构建系统: autotools（SourceForge 发布 tarball 自带 configure）
- 编译日期: 2026-09-14
- 编译器: clang 15.0.4（OHOS aarch64）
- 状态: built

## 编译步骤

1. init-build 预下载后改用官方 SourceForge 发布 tarball（sha256=5652b391…d9d4e）——GitHub tag 归档无预生成 configure，CI 无法保证 autoreconf 工具链。
2. conan-init 生成骨架后手写配方（以归档 vo-aacenc/0.1.3 为范式，static-library）。
3. `conan-verify` 完成 conan create + 消费者测试（消费者程序真实编译、链接、运行并断言）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 首轮 conan create 消费者测试编译失败：`enc_if.h file not found` | 头文件安装到 `include/vo-amrwbenc/` 子目录（amrwbencincludedir），非 include 根 | test.c 改为 `#include <vo-amrwbenc/enc_if.h>`（下游正确用法） |
| 2 | configure 内嵌 `umask 077` mktemp 探针 | HMDFS 权限组合使 config.status 临时目录不可写（E011 同源） | 配方 build() 中 replace_in_file 放宽为 umask 022（vo-aacenc 同值） |
| 3 | config.sub 不识别 linux-ohos triplet | 2010 年代 config.sub 无 ohos 支持 | `--build`/`--host` 均传 aarch64-unknown-linux-gnu（vo-aacenc 先例） |

## 源码修改

无补丁文件（conandata 无 patches）；适配动作在 conanfile.py build() 内完成（configure 的 umask 放宽）。

## 依赖版本

无第三方依赖（configure 只探测编译器与 libtool；amrwb-enc 示例默认 `--enable-example` 关闭，不引入 wav 依赖路径）。

## 上游测试四维账本

- 上游静态声明总数：**0**。R51 清点证据：上游 Makefile.am 仅有 `lib_LTLIBRARIES`、`amrwbencinclude_HEADERS`、`pkgconfig_DATA` 与条件汇编/示例目标，无 `TESTS`/`check` 目标、无 `check_PROGRAMS`，源码树无 test/ 目录。
- 实际执行：0（上游无测试可执行）
- 新增消费者测试：1 个程序（test_package/test.c，经 CMake 链接 libvo-amrwbenc，调用公开 API `E_IF_init`/`E_IF_encode`/`E_IF_exit`，3 处断言：两帧 mode 8 编码输出恰为 61 字节 RFC 3267 帧 + 载荷非全零）——已在 conan create 真实构建中编译、链接并运行通过。

## 验证结果

```bash
# conan create（设备，ohos-aarch64 profile）
$ conan-verify vo-amrwbenc 0.1.3
G0-G4 全部 PASS（含消费者测试在 test_package 中真实运行）
# 消费者程序输出：
vo-amrwbenc consumer test passed (two 61-byte AMR-WB frames)
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libvo-amrwbenc.a | AMR-WB 编码器静态库 |
| include/vo-amrwbenc/enc_if.h | 公开编码 API 头文件 |
| lib/pkgconfig/vo-amrwbenc.pc | pkgconfig 描述文件 |
| licenses/NOTICE | Apache-2.0 许可声明 |

## 注意事项

- aarch64（armv8）下 `armv5e`/`armv7neon` 汇编分支默认关闭（configure 默认值 no），纯 C 编译，无需处理 ARM 32 位 .s 汇编。
- 上游无自动化测试，按 R51 如实申报 0 并附清点证据；赛道二消费者测试以真实 API 调用+断言补位。
---

**编译结束**: 2026-09-14 01:32
**最终状态**: built

## 对话记录

- 2026-09-14 GLM-24: 完成适配、conan-verify（G0-G4 通过）与设备端 finish/W3 验证；上游无自动化测试（R51 清点见 MANIFEST.yml），消费者测试 1 程序 3 断言真实编译链接运行通过。
