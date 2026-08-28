# lzsa 1.4.1 — OpenHarmony 编译记录

## 基本信息
- 软件: lzsa
- 版本: 1.4.1
- 构建系统: makefile
- 目标: ohos-aarch64
- 上游: https://github.com/emmanuel-marty/lzsa
- sha256: c65ca1e6a43696f4ca5edc2c98229fba1044806bd21bc2a8ce4b867dc9cfc45c
- 许可: CC0-1.0（代码）, Zlib（divsufsort）
- 依赖: 无
- 产物: 仅 CLI（Makefile 无 lib/.a/.so 目标, cpp_info.libs=[]）

## 编译指导
- 纯 Makefile 构建, CC=clang 可通过命令行覆盖（Makefile 使用简单 = 赋值）
- make -j1（HMDFS jobserver FIFO EPERM，E074）
- CC= 通过 make 命令行显式传入 OHOS arm64 clang, 命令行赋值优先于 Makefile 内 = 赋值
- CFLAGS 覆盖: 丢弃 -fomit-frame-pointer, 保留 -O3 + -Isrc/libdivsufsort/include -Isrc
- 零补丁: 上游 Makefile 无硬编码平台/路径, config.guess/config.sub 不适用

## 补丁清单
- 无（零补丁）

## 已知限制
- lzsa 仅提供 CLI 工具, 无库目标（.a/.so）, 不能作为库依赖被其他包链接
- 上游 Makefile 有 test 目标（./lzsa -test 内置自测）, 功能验证由 test_package
  真实执行 lzsa 二进制（-test 自测 + 格式2/格式1 压缩/解压往返内容比对）完成

## 功能验证
- test_package/test_lzsa.sh: lzsa -test 自测 + 格式2(默认)/格式1(-1) 压缩→解压往返
  cmp 内容一致 + 压缩率健全性检查（压缩文件 < 原始文件）
