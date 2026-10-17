# srf 0.1 — 适配笔记（notes.md）

## 概览

srf 0.1+dfsg（Debian 官方池镜像）— 2008 年代 SRF DNA 测序容器 C++ 实现，
autotools maintainer-mode 构建，静态库 libsrf.a + 4 个消费者程序。
依赖 io_lib/1.14.9（libstaden-read，PR #14040 链）。

conan create 全绿（--build=missing -pr:h ohos-aarch64 -pr:b default），
test_package 消费者测试 `PASS: srf roundtrip (reads=1)`。

## 补丁清单（0001-0004）

| 补丁 | 内容 | 根因 |
|---|---|---|
| 0001 explicit-int-main | 4 个测试程序 `main()` → `int main()` | clang C++11 对 implicit-int 硬错误 |
| 0002 configure-umask-tmpdir | `umask 077`→`022`（config.status 内嵌临时目录逻辑） | HMDFS 忽略 chmod，700 临时目录创建者自己不可写 → config.status 假成功（rc=0 但 Makefile 全缺）。commoncpp2/io_lib 同款 |
| 0003 iolib-config-param | `AC_ARG_VAR IO_LIB_CONFIG` 参数化 + 去 `-lread` | io_lib-config 内嵌构建机绝对路径，下游不可依赖其输出；上游 LDLIB 的 `-lread` 是 2008 年旧名 |
| 0004 missing-return | 4 个非 void 函数补 return | 见下节（本库最深坑） |

## 核心坑：non-void 函数缺 return → arm64 clang brk 陷阱（0004）

**现象**：任何调用 SRF C++ API 的程序 SIGTRAP/SIGSEGV，崩点随优化级别漂移
（-O0 崩在 write() 返回后、-O3 崩在 write() 内部），ASAN 无报告（是编译器
埋的陷阱不是内存越界），gdb 被 SELinux 挡无法 attach。

**定位过程**（15+ 轮实验收敛，记录供同类问题复用）：
1. 信号 handler 打印 `/proc/self/maps` 修正 PIE 基址 → 崩溃 pc 换算为真实 vaddr
2. ⚠ 关键：handler 打印的"映射内偏移"≠ ELF 文件偏移，须按 program header
   （r-xp 段 vaddr）换算成 vaddr 后再 llvm-symbolizer/objdump——此前两轮
   符号化全部错位在此
3. llvm-objdump 反汇编崩溃点：`brk #0x1` 紧跟 `fprintf@plt` 之后、位于
   `SRF_Container::write` 收尾大括号 → clang 对"非 void 函数掉出函数尾"UB
   的标准处置（2008 gcc/x86 侥幸返回垃圾值，新 arm64 clang 埋陷阱）
4. `-Wreturn-type` 全量扫描 → 4 处：SRF_Container::write / SRF_Read::write /
   SRF_ReadSet::write / SRF_writeZtr，补 `return TRUE;`/`return 0;`

**教训**：诊断期间一直加 `-w` 压掉了告警，等于亲手关掉了编译器的提示。
移植老库第一件事应保留 `-Wreturn-type` 级别的警告做一轮语法扫描。

## 其他适配要点

- **tarball 无 config.guess/config.sub**：但 configure 同样无 AC_CANONICAL_*
  （不调用），无需注入；属 KB-ATBOOT A 类检测项的"免修"样例
- **`$(SHELL io_lib-config ...)` 非 GNU make 函数**：展开为空串（静默），
  io_lib 头/库路径走 CPPFLAGS/LDFLAGS env 通道注入（io_lib 已验证生效）
- **maintainer-mode 时间戳链**：patch 后按依赖序（configure.in → aclocal.m4 →
  configure → *.am → *.in）把 mtime 刷到过去；"过去"而非"现在"才能过
  configure 的 `ls -t` sanity 检查（E248 同源，KB-ATBOOT B' 类）
- **上游无 install-headers 规则**：package() 手动补装 src/*.hh
- **io_lib-config 不可依赖**：内嵌构建期绝对路径（io_lib 适配结论沿用）

## KB-ATBOOT 样例库验证（知识库拓展样例，knowledge/tools/kb-atboot/）

| 阶段 | 结果 |
|---|---|
| detect（未修复） | `HIT-A: missing config.guess,config.sub`（rc=1） |
| reproduce phase1（关 SKILL） | reproduced（rc=0 假成功 + Makefile 三件全缺） |
| fix | FIX-A 注入 config.guess/sub + FIX-B umask 077→022 |
| reproduce phase2（开 SKILL） | fixed（Makefile 三件全生成） |

## R51 上游测试实测

4 个消费者程序 4/4 通过（详见 reports/test-report.md）：
testWrite→myFirstSSRFFile(1091B)、testRead 读回容器头、
testWriteFastaq→fastaOut.srf、testWriteSFF→sffOut.srf（最小 SFF 魔数头）。

## 依赖链

- io_lib/1.14.9（PR #14040，已发布后本 PR 方可过 PF4）
- libcurl/zlib/bzip2/lzma：io_lib 传递依赖（制品仓已有）
