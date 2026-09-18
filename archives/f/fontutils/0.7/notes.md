# fontutils 0.7 适配笔记 (GLM-30, 2026-09-15)

## 任务
- 平台任务号: 13461 (开源鸿蒙PC专项积分赛-依赖, activity_id=6)
- 分支: feat/fontutils-0.7 (基于 upstream/main 6b5087b97a)
- 上游: https://ftp.gnu.org/gnu/fontutils/fontutils-0.7.tar.gz
- sha256: 75d44bdfc4002238f4ebcba857b913b57ae9e5b356416413f4776f832409939e
- worktree: ~/qzy/GLM-30-fontutils-0.7
- CONAN_HOME: ~/tmp/ch/home-glm30-fontutils

## 上游概况
GNU fontutils 0.7 (2000): 位图/轮廓字体转换工具集 (bpltobzr/bzrto/charspace/
fontconvert/gsrenderfont/imageto/imgrotate/limn + X11 编辑器 xbfe)。
自研 GNUmakefile 顶层脚本 + 每目录 GNUmakefile/Makefile.in 混合构建, 非 automake 标准布局。

## 语言/构建预检
- lang-preflight: c:151 文件 100% (通过)
- 构建系统: 自定义 GNUmakefile (autotools 家族, 配方走 autotools helper)

## 测试四维账本
- N_static = 0: 上游无测试套件。证据: GNUmakefile.in:222 check 目标仅打印
  "No validation suite in this directory."; tarball 无 test*/ 子目录与测试程序。
- N_registered = 0 / N_executed = 0: 无可执行上游测试。
- N_consumer = 1: test_package 运行打包后的 bpltobzr, 将最小 BPL(文本)字体
  转换为 BZR(二进制)字体, 断言产物存在且非空 (112 bytes)。
- N_assertion = 2: 输出文件存在 + 大于 0 字节。

## 主要适配点 (patches/0001-fix-ancient-code-for-ohos-clang.patch, 14 文件)
1. config.guess/config.sub 过老(2000): 由 source() 用 autoconf 2.72 现代脚本
   (compat/) 覆盖, 并显式传 --build/--host=aarch64-unknown-linux-ohos。
2. widgets 的 Makefile 以 `-I..$(top_srcdir)/include` 拼接包含路径: conan 传入
   绝对 srcdir 时变成非法 `-I..//...`; 显式 `--srcdir=.` 保持相对 (in-tree)。
3. 顶层 GNUmakefile 用 `cd subdir && make` 遍历: 必须 in-tree 构建
   (layout: folders.source=folders.build=".")。
4. HMDFS 禁止 make jobserver FIFO (GNU Make 4.4): make -j1 绕过。
5. 古董 C 代码 clang 兼容: malloc.c 绝对路径 `#include "//usr/include/stdio.h"`
   改 `<stdio.h>`; 其 getpagesize 级联(未移植宏 NBPC)改用 unistd.h;
   旧式 sbrk 声明冲突删除; 内部 unlink 函数与 unistd 冲突改名 mu_unlink;
   cmdline.h/tfm_input.c/bzr_input.c/gf_input.c 的多行字符串字面量改标准拼接;
   fmod.c 删除 K&R `extern int isnan(),finite();`; now.c 补 <time.h>。
6. X11 剔除: widgets 库与 xbfe 编辑器从 libraries/programs 剔除; limn 的
   display.c 桩化(保留 wants_display 等导出变量与空函数), xserver.c 不再编译。
7. 捆绑 GNU malloc 93 (lib/malloc.o) 在 64 位 OHOS 崩溃(指针截断): 按上游
   Makefile 自带说明移除 (`malloc =`), 使用 musl malloc。
8. tarball 自带陈旧 M.depend(引用 //usr/include): recipe build() 删除,
   defs.make 规则以 $(CC) 重新生成 (defs.make 同时修 CC=gcc 硬编码 -> CC ?= gcc)。
9. OHOS 无 coreutils install: compat/install shim (cp+chmod 子集),
   autotools.install(args=["prefix=<pkg>", "INSTALL=<shim>"]) 显式覆盖;
   prefix 显式传入以修复 layout 覆盖导致的空 datadir。

## 消费者测试
test_package/test.bpl (最小 BPL 字体, 1 字符 65 方框轮廓) -> bpltobzr 转换 ->
断言 *.bzr 存在且非空。运行于隔离临时目录, 不污染归档树。

## 路径 B 判断
不走 B。理由: 修复均为包内古董代码的平台适配 (K&R/多行字符串/X11 剥离/
捆绑 malloc 剔除), 其中 jobserver FIFO (E 条目已有)、config.guess 刷新
(abiword-plugin 系配方先例)、umask/HMDFS 类问题均已有知识覆盖; 未形成新的
可跨仓库复用知识增量。依据记录于本文件, 结论: 纯路径 A。

## 已知限制
- xbfe (X11 位图编辑器) 与 widgets 库未纳入产物 (X11 依赖, OHOS 无 X11)。
- info 文档未安装 (无 makeinfo/texinfo), doc install 置为 no-op。
---

**编译结束**: 2026-09-17 05:47
**最终状态**: built
