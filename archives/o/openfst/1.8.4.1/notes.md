# openfst 1.8.4.1 适配笔记

## 版本说明

- 上游版本：openfst **1.8.4**（源码 tarball 与 1.8.4 完全相同）
- 本版本号 **1.8.4.1**：同一上游版本的「适配修复版本」（R37），与 1.8.4 的唯一差异 =
  `configure` 增加 `--enable-grm`
- 变更动机：上游 `configure.ac` 中 `--enable-far` / `--enable-pdt` / `--enable-mpdt` /
  `--enable-grm` 默认值**均为 no**，因此已发布的 openfst/1.8.4 包内 **不含**
  `include/fst/extensions/{far,pdt,mpdt}`。下游 OpenGrm Thrax 1.3.10 的 `configure`
  对 `fst/extensions/far/far.h`、`pdt/pdt.h`、`mpdt/mpdt.h` 做 `AC_MSG_ERROR` 硬校验，
  缺头文件即构建失败。
- `--enable-grm` 在上游是 far + mpdt + pdt 的**聚合别名**，一次开启三者。

## 编译环境

- 构建系统: autotools
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. `ohc-run.py init-build openfst 1.8.4.1 --url=<官方 1.8.4 tarball>` — 下载、解压、骨架创建
2. 复用 1.8.4 的 4 个平台补丁（config.guess / config.sub / configure / flags-help-exit），源码相同故补丁原样适用
3. `./configure --prefix=$DEFAULT_PREFIX --enable-bin --enable-grm --enable-static --disable-shared`
4. `make -j1`
5. `make check`（构建目录内，install 前执行）
6. `conan create`（conan-verify / W3）复现干净构建 + test_package 冒烟

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 已发布 openfst/1.8.4 不含 GRM 扩展 | 上游 configure 默认 `far/pdt/mpdt=no`，配方未显式开启 | 本版本 configure_args 增加 `--enable-grm`（far+mpdt+pdt 别名） |
| 2 | config.guess 不识别鸿蒙平台 | 缺少 aarch64-ohos 三元组 | 补丁 0001-config.guess.patch（沿用 1.8.4） |
| 3 | config.sub 不识别 ohos | 缺少 ohos 操作系统条目 | 补丁 0002-config.sub.patch（沿用 1.8.4） |
| 4 | configure 中 pipe/cat 语句失败 | toybox sh 对复杂引号处理差异 | 补丁 0003-configure.patch（沿用 1.8.4） |
| 5 | CI 通用 smoke check 将 `--help` 退出码 1 视为失败 | OpenFst flag 处理将帮助输出作为错误退出 | 补丁 0004 将 `--help` / `--helpshort` 退出码改为 0（沿用 1.8.4） |
| 6 | make check 无法在 install 后重跑 | Makefile 被清理 | 在构建目录、install 前执行 make check |

## 源码修改

与 1.8.4 完全一致（源码 tarball 相同），补丁 4 个：

- `config.guess`: 添加 aarch64-ohos 识别规则（补丁 0001）
- `config.sub`: 添加 ohos 操作系统支持条目（补丁 0002）
- `configure`: 修复 shell 引号兼容性问题（补丁 0003）
- `src/lib/flags.cc`: 显式帮助请求返回成功状态（补丁 0004）

> 本版本**未**新增源码补丁：GRM 开启完全通过 configure 选项实现，不涉及 `#ifdef` 平台宏。

## 上游测试

- 上游自带测试：autotools `make check` 目标（`src/test/` 下的 fst_test + algo_test 系列）
- 清点与实测结果见下方「测试结果」小节

## 测试结果

### 1) 上游测试实跑：`make check`（构建目录内、install 前执行）

```
# TOTAL: 7   # PASS: 6   # FAIL: 1   # SKIP: 0   # XFAIL: 0   # ERROR: 0
PASS : algo_test_tropical, algo_test_log, algo_test_minmax,
       algo_test_lexicographic, algo_test_power, weight_test
FAIL : fst_test
```

`fst_test` 失败实测输出与根因：

```
FATAL: Error loading shared library vector-fst.so: No such file or directory
```

- 上游 `fst_test` 走 FST **动态类型注册**，运行时 `dlopen` 加载 `vector-fst.so` 插件；
- 本配方与已发布的 openfst/1.8.4 一致为**静态构建**（`shared=False` → `--disable-shared`），
  构建树与包内均不产出 `*-fst.so` 插件（实测 `find -name '*-fst.so'` 结果为空）；
- 故该失败是「静态构建 vs 需要动态插件的用例」组合导致，**与 OHOS 平台适配无关**，非本
  版本引入的回归（1.8.4 同为静态配方）；历史 1.8.4 手工构建（默认 shared）记录为 7/7 通过。

### 2) L2 冒烟（对打包产物实际执行）

| 命令 | 结果 |
|------|------|
| `fstcompile --help` | exit 0 ✅ |
| `farcompilestrings --help`（GRM 工具） | exit 0 ✅ |

### 3) GRM 扩展产物核验（本版本核心目的）

| 项 | 实测 |
|----|------|
| 头文件目录 | `include/fst/extensions/{far,pdt,mpdt}` 三者齐全，含 `far.h` / `pdt.h` / `mpdt.h` ✅ |
| 静态库 | `libfst.a`、`libfstscript.a`、`libfstfar.a`、`libfstfarscript.a`、`libfstpdtscript.a`、`libfstmpdtscript.a`（6 个） |
| GRM 命令行工具 | 19 个（farcompilestrings / farconvert / farcreate / farencode / farequal / farextract / farinfo / farisomorphic / farprintstrings / mpdtcompose / mpdtexpand / mpdtinfo / mpdtreverse / pdtcompose / pdtexpand / pdtinfo / pdtreplace / pdtreverse / pdtshortestpath） |
| 产物规模 | bin 56 + lib 12（6 .a + 6 .la）+ header 204（1.8.4 为 37/…/107，差值即 GRM 产物） |

> 结论：`--enable-grm` 生效，下游 OpenGrm Thrax 1.3.10 configure 所需的
> `fst/extensions/{far,pdt,mpdt}` 头文件已随包提供，可解除 thrax 构建阻塞。

## 依赖版本

- 无外部库依赖
- 运行时依赖: libc++_shared.so（clang C++ 运行时）、libc.so（系统库）

## 注意事项

- `fstcompile` 不支持 `--version`，使用 `--help` 验证；`--help` / `--helpshort` 返回 0
- `make check` 需在 install 前执行
- 下游引用请使用精确版本：`self.requires("openfst/1.8.4.1")`（需要 GRM 扩展的包必须 ≥ 1.8.4.1）

---
**编译结束**: 2026-10-03
**最终状态**: built
---
---

**编译结束**: 2026-10-03 14:30
**最终状态**: built
