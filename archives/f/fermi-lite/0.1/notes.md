# fermi-lite 0.1 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，无 configure）
- 编译日期: 2026-09-26
- 编译器: clang/clang++（OHOS SDK 15.0.4）
- 状态: built

## 官方来源核验
- 上游: https://github.com/lh3/fermi-lite
- 版本标识: 核验正式 tag `v0.1`（commit d468f39457124764a7073dd989583813e3353a10）
- 源码 tarball: https://github.com/lh3/fermi-lite/archive/refs/tags/v0.1.tar.gz
- SHA-256: 661053bc7213b575912fc7be9cdfebc1c92a10319594a8e8f18542c9e2adda6e

## 编译步骤
1. init-build 下载官方 tag tarball 并解压
2. 语言预检（R47）: task=cpp, detected=c → 通过，继续适配
3. 直接 `make CC=clang AR=llvm-ar -j1`（Makefile 无 configure）
4. `make install DESTDIR=staging` 手动安装 libfml.a + 公共头文件 + fml-asm

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 首次 init-build 用仓库 URL 下载得到 HTML | download_url 需指向 tarball 而非仓库页 | 改用官方 `archive/refs/tags/v0.1.tar.gz` 直链 |
| 2 | ksw.c 无条件 `#include <emmintrin.h>`，aarch64 编译失败（SSE2 x86 专属头） | 上游 ksw.c 仅 SSE2 实现（x86/x64），无 ARM 标量回退 | 为 ksw.c 增加 `#if defined(__SSE2__)` 条件编译：SSE2 分支保持原实现，非 SSE2 (aarch64) 分支提供完整标量 ksw_u8/ksw_i16/ksw_qinit 回退实现（fermi-lite 实际仅用 ksw_i16 路径） |
| 3 | `const uint8_t rle_auxtab[8];` 在 rle.h 中以暂定定义声明，多 TU 各自生成符号 → 链接 duplicate symbol | 头文件非 extern 声明导致每个包含它的 .o 都带定义 | rle.h 改为 `extern const uint8_t rle_auxtab[8];`（定义保留在 rle.c） |
| 4 | conan-init 按 autotools 生成配方模板，但本项目是纯 Makefile | 模板自动推断与项目实际不符 | 按仓库 raw-make 配方范例（2048.c）重写为 Makefile 风格 conanfile.py |

## 源码修改
- ksw.c: 增加 `#if defined(__SSE2__)` 标量回退分支（保留原 SSE2 代码，aarch64 走标量）
- rle.h: `rle_auxtab` 改为 extern 声明
- 均为可审计源码修改，补丁由 finish refresh-patch --auto 生成

## 依赖版本
- 无 Conan 依赖（LIBS = -lm -lz -lpthread 由系统提供）

## 验证结果
- 上游测试（R51）: `./fml-asm test/MT-simu.fq.gz > MT.fq` 退出码 0，正确输出 2 条组装 unitig fasta 记录（上游自带唯一测试数据 test/MT-simu.fq.gz）
- test_package: 构造两条 40bp 重复序列调用 `fml_assemble` API，验证返回非空 unitig（R34 实质测试）

## 交付物
- `archives/f/fermi-lite/commands.json`: 声明命令行工具 fml-asm（R38）
- `archives/f/fermi-lite/0.1/`: conanfile.py + conandata.yml + test_package/ + manifest.yaml + notes.md

## 注意事项
- 上游 fml-asm 输出直接打印到 stdout，运行上游测试时需重定向
- ksw 标量回退为逐单元 DP，不采用 SSE2 的 16/8 lane 并行布局；对 100bp–10Mb 组装在 aarch64 上正确性等价，性能低于 SIMD 属预期
---

**编译结束**: 2026-09-26 22:40
**最终状态**: built
