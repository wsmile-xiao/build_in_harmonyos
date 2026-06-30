# icarus-verilog 12.0 适配笔记

## 编译环境
- 构建系统: autotools (需要 autoconf.sh bootstrap)
- 编译日期: 2026-06-03
- 编译器: clang/clang++
- 状态: built

## 构建流程（重要）

icarus-verilog 的 GitHub tag tarball **不含 configure 脚本**，构建步骤：

1. **Bootstrap**: 运行 `autoconf -f`（仅生成 configure，不要运行完整 `autoconf.sh`）
   - ⚠️ `autoconf.sh` 会调用 gperf 重新生成 `lexor_keyword.cc` 和 `vhdlpp/lexor_keyword.cc`
   - ⚠️ 重新生成的 bison/flex/gperf 输出会导致 clang 崩溃（SIGSEGV on 大文件如 parse.cc 18497行）
   - ✅ tarball 中已有预编译的 bison/flex/gperf 输出，它们能正常被 clang 编译
   - **关键**：不要让 make 重新生成 bison/flex/gperf 输出，使用 tarball 中已有的版本
2. **Configure**: `./configure --prefix=$DEFAULT_PREFIX`
3. **Make**: `make -j1`（避免并行竞态）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 原有 60 个 patch，58 个是生成文件 | `per-file-difflib` 比对含构建产物的 work 目录 | 按 R6 铁律删除，只保留 config.guess/sub |
| 2 | clean-verify configure 失败: "no closing quote" | tarball 不含 configure，脚本直接跑 ./configure | 需先运行 `autoconf -f` 生成 configure |
| 3 | clang 在 regenerated parse.cc 上 SIGSEGV | 本地 bison 生成的 parse.cc 过大(18497行)致 clang 崩溃 | 不重新生成，使用 tarball 预编译版本 |

## 补丁清单（精简后）

| # | 文件 | 说明 |
|---|------|------|
| 0001 | config.guess.patch | 添加 HarmonyOS 平台检测 |
| 0002 | config.sub.patch | 添加 `-harmonyos*` OS 识别 |

## 源码修改

仅修改了 config.guess 和 config.sub（源文件），所有其他差异都是构建产物。

## 注意事项

1. **不要运行 `autoconf.sh`**——只运行 `autoconf -f`。完整 autoconf.sh 会覆盖预编译的 gperf 输出。
2. **不要让 make 重新生成 bison/flex/gperf**——clang 会崩溃。如果 make 触发重新生成，需要 touch 预编译输出文件使其时间戳更新。
3. **make 用 -j1**——避免 vhdlpp 竞态问题（package_emit.d mv error）。