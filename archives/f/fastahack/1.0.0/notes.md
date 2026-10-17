# fastahack 1.0.0 — 适配笔记

## 基本信息
- 上游: https://github.com/ekg/fastahack (Erik Garrison, Marth Lab, Boston College)
- 版本: v1.0.0 tag (2019-09-04, commit bb332654)
- 功能: FASTA 文件索引(.fai)、子序列/全长序列提取、Shannon 熵、dump
- 构建系统: 纯 Makefile（无 configure 脚本）
- 产物: 单个 CLI 可执行文件 `fastahack`（R38 需 commands.json）
- License: MIT

## 构建命令
```
make CXX=clang++ CXXFLAGS="-O3 -fPIC -D_FILE_OFFSET_BITS=64" -j1
make install DESTDIR=$DEST PREFIX=/usr/local
```
上游 Makefile 默认 CXX=g++，需覆盖为 clang++（R33：从 Conan conf 取编译器）。

## 适配修复
1. **LargeFileSupport.h: `__off64_t` → `off_t`**（patch 0001）
   - 首错: `LargeFileSupport.h:15:9: error: unknown type name '__off64_t'`
   - 根因: `__off64_t` 是 glibc 私有 typedef，OHOS musl libc 不提供。
   - 修复: 用标准 `off_t`（该文件已 `#define _FILE_OFFSET_BITS 64`，off_t 同为 64 位，语义等价）。
   - 验证: 修改后 `make` 编译通过，`file fastahack` 为 arm64 ELF。

## 测试
- 上游无 make check target；tests/ 目录为 5 个 FASTA 测试数据文件（fixture）：
  - correct.fasta: 标准 3 序列文件 → 索引 OK，-r 提取 OK
  - crlf.fasta: CRLF 行尾 → 索引 OK，-r chr 提取 OK
  - trailing_newlines.fasta: 尾部换行 → 索引 OK，-r 提取 OK
  - embedded_newline.fasta: 序列内嵌换行 → 按 README 声明拒绝索引（预期行为）
  - mismatched_lines.fasta: 行长度不一致 → 按 README 声明拒绝索引（预期行为）
- test_package: CLI 烟雾测试（usage 横幅 / .fai 生成 / -r 子序列提取比对 / -e 熵数值 / -d dump）
- 鸿蒙专项 LFS 测试（reports/ohos-lfs-test.sh）: 构造 3×~1GB（总 3GB）FASTA，
  索引后从 seq3（偏移 2,000,070,160 > 2GB）提取子序列成功 —— 证明
  __off64_t → off_t 修复后 fseeko/ftello 64 位偏移在 OHOS musl libc 下正常工作。

## 消费者验证
test_package/test.sh 通过 `fastahack -i` + `-r 1:1..20` 提取 correct.fasta 序列 1 前 20 bp
（TAACCCTAACCCTAACCCTA）并断言与上游序列一致 —— 真实调用公开 CLI API 并有可观察输出。

## 知识候选
- OHOS musl libc 缺 glibc 私有 `__off64_t` 类型 → 用标准 off_t 替换（知识库查重未命中，候选路径 B）
---

**编译结束**: 2026-09-21 16:44
**最终状态**: built
