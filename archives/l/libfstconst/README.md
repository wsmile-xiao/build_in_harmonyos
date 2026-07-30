# libfstconst

libfstconst 是 OpenFst 的 ConstFst 扩展库，提供不可变（immutable）有限状态转换器的紧凑数组表示。

## 描述

OpenFst 是开源的加权有限状态转换器（FST）库。ConstFst 扩展把状态和弧分别存放在单一数组中，适合读多写少的不可变 FST，相较通用 Fst 实现有更低的内存占用与更快的随机访问性能。

本包只构建 ConstFst 扩展库（`libfstconst.so` / `libfstconst.a`），不构建 fst::script 与命令行二进制。

## 版本列表

| 版本 | 状态 | 编译日期 | 测试状态 |
|------|------|----------|----------|
| 1.8.4 | built | 2026-07-28 | 上游 make check 7/7 通过 |

## 鸿蒙平台适配

复用 openfst 1.8.4 已验证的平台补丁：

1. `config.guess` — 添加 aarch64-ohos 平台识别（E007）
2. `config.sub` — 添加 linux-ohos 三元组（E007）
3. `configure` — 修复 toybox sh 下引号兼容性（E064）
4. `src/lib/flags.cc` — 显式 `--help` 请求返回成功（E081）

编译要点：
- autotools 构建，`--enable-const-fsts` 单独启用本扩展，其余扩展与命令行二进制全部 `--disable-*` 关闭
- 无外部库依赖，运行时仅需 libc++_shared.so 与 libc.so

## 依赖关系

- 编译依赖：无
- 运行时依赖：libc++_shared.so（clang C++ 运行时）、libc.so（系统库）
- 上游 openfst 的核心库（libfst.so/libfstscript.so）由 openfst 1.8.4 配方提供，本包独立 ConstFst 扩展库

## 参考资料

- 官网：https://www.openfst.org/
- 源码：https://openfst.org/twiki/pub/FST/FstDownload/openfst-1.8.4.tar.gz
- ConstFst 文档：https://www.openfst.org/doxygen/fst/html/classfst_1_1ConstFst.html

---

*最后更新：2026-07-28*
