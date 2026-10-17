# LAST (last-align) 1652 适配笔记

## 编译环境
- 构建系统: makefile（plain Makefile，非 autotools）
- 编译日期: 2026-09-19
- 编译器: clang 15 / clang++ 15（OHOS SDK）
- 状态: built（conan-verify 待跑）

## 编译步骤

LAST 是 plain Makefile 项目，无 configure 脚本。顶层 `makefile` 委托 `src/makefile` 编译：

```bash
make -j1                    # 在源码根目录执行，产物写入 bin/
make install prefix=$PREFIX # 顶层 makefile 忽略 DESTDIR，用 prefix 覆盖
```

编译核心产物（5 个 ELF 可执行文件）：
- `bin/lastdb` — 建索引
- `bin/lastal` — 序列比对
- `bin/last-split` — 比对结果拆分
- `bin/last-pair-probs` — 配对读长距离估计
- `bin/last-merge-batches` — 合并比对批次

另含上游自带的 Python3/Bash 辅助脚本（maf-convert、last-train、last-dotplot 等）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CXXFLAGS 默认含 `-msse4` | LAST 为 x86 SSE4 优化，aarch64 上 clang 报 unused-argument warning | 配方 `_make_arguments()` 覆盖 CXXFLAGS（-O3 -std=c++11 -pthread）|
| 2 | 顶层 makefile install 忽略 DESTDIR | 安装规则直接 `mkdir -p $(bindir); cp bin/* $(bindir)` | 探索阶段用 `prefix=$TEST_PREFIX`；配方 package() 直接 copy bin/ |
| 3 | 上游测试脚本硬编码 `/tmp` | HarmonyOS `/tmp` 只读（E002） | 测试运行设 TMPDIR；last-test.sh/last-train-test.sh/last-dotplot-test.sh 三脚本硬编码 /tmp 需在可写目录运行 |
| 4 | `-lz` 链接 | 需要 zlib | 配方 requirements 声明 zlib/1.3.1，CPPFLAGS/LDFLAGS 注入其 include/lib 目录 |
| 5 | 部分辅助脚本（last-dotplot/last-map-probs）需 Python PIL/matplotlib | 上游脚本依赖未捆绑的 Python 模块 | 平台限制记录，核心 ELF 工具不受影响 |

## 源码修改

无补丁（patches/ 为空）。`src/mcf_simd.hh` 原生支持 `__ARM_NEON`，aarch64 自动选择 NEON SIMD 路径，无需平台补丁。

## 依赖版本

- zlib/1.3.1（Conan 制品仓 ohpcd 已发布，W0 验证通过）

## 验证结果

```bash
# 5 个核心二进制 --version 全部正常
lastdb 1652
lastal 1652
last-split 1652
last-pair-probs 1652
last-merge-batches 1652

# 上游测试（R51 实测）
# last-test.sh 主套件 68 个子测试：全部运行，score/序列内容与参考一致；
#   差异仅为 aarch64 NEON 与 x86 SSE 的 tied-position 排序（上游文档 lastdb.rst 明确此行为）
# last-split / maf-convert / maf-cut / maf-linked / maf-swap / last-postmask: PASS
# last-train: PASS（路径归一化后仅 1 处空行差异）
# last-map-probs: 仅 2 行浮点精度差异（9.22e-12 vs 9.24e-12，统计估计末位）
# last-pair: 因 fastq-interleave 脚本 #!/bin/bash 不可用（OHOS 无 /bin/bash）
# last-dotplot: 因缺 Python PIL 模块
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/lastdb | ~326K | 索引构建工具 |
| bin/lastal | ~1.3M | 序列比对工具 |
| bin/last-split | ~260K | 比对拆分工具 |
| bin/last-pair-probs | ~105K | 配对读长分析 |
| bin/last-merge-batches | ~23K | 批次合并工具 |
| bin/maf-convert 等 | — | 上游 Python/Bash 辅助脚本 |

## 注意事项

- LAST 许可证为 **GPL-3.0-or-later**（源码 COPYING.txt），非模板默认的 MIT。
- 顶层 makefile install 不支持 DESTDIR，conan package() 直接用 copy 打包 bin/。
- 测试硬编码 `/tmp` 是 R51 上游测试在本平台运行的主要限制（E002），已在 MANIFEST.yml 申报。
- 上游没有 `make check` 目标；测试为 test/*.sh 独立回归脚本，需逐个运行。
---

**编译结束**: 2026-09-19 14:50
**最终状态**: built
