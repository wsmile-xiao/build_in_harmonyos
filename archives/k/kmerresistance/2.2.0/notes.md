# kmerresistance 2.2.0 适配 notes

## 概况
- 软件类型：C99 命令行工具（raw Makefile，无 configure），产物 `kmerresistance` 单可执行。
- 语言预检（R47）：task=cpp / detected=c，c↔cpp 兼容族，通过。
- 依赖：源码仅 libc/libm。**无 zlib 依赖**（bioinformatics 领域但源码无 gz* 符号，逐文件扫描验证 KmerResistance.c/pherror.c/qseqs.c）。W0 预检 zlib 已发布（zlib/1.3.1，recipe 2ee7c0ee…）。
- 平台宏：无平台补丁，patches/ 为空。`#define _XOPEN_SOURCE 600` 上游自带，OHOS clang 直接编译通过。

## 编译
- `make -j1 CC=clang`（conan recipe 从 tools.build:compiler_executables 取值，R33 合规）。
- 本机 clang 15.0.4（aarch64-unknown-linux-ohos）原生编译通过，零警告错误。

## 上游测试
- 上游 tarball 无任何测试套件（仅 KmerResistance.c/pherror.c/h/qseqs.c/h/Makefile/README.md；Makefile 只有 all/clean 目标）。故以 test_package 功能测试代替：7 项断言（版本 banner、help、缺参拒绝、全管线运行、DONE 标记、物种相关输出、基因结果输出）全部通过。

## 关键事实：运行时外部依赖 kma
- kmerresistance 通过 system() 调用外部 `kma`（KMA 是独立上游项目，本包不含），未打包的 kma 属于**外部运行时依赖**（用户需自行安装 KMA 并建立索引库）。
- test_package 用 stub kma + 合成 FASTQ/KMA 输出夹具验证全管线（对齐 abbtr 等 application 包先例）。
- 已在 req 图谱登记 kma 需求（ohc-run.py req add）。

## 环境注意
- /tmp 只读，测试用 mkdtemp "$TMPDIR/..."（$TMPDIR=/storage/Users/currentUser）。
- make -j2 会因 jobserver mkfifo 权限失败（HMDFS），一律 -j1。
---

**编译结束**: 2026-09-20 09:00
**最终状态**: built

## 提 PR 说明
- 本包为 CLI 工具，按 R38 在软件级目录提交 `commands.json`（CI L0k 必查）。
- preflight PF9（v12.20）要求 archives 变更全部落在 包/版本/ 目录，对软件级 commands.json/manifest.yaml 无豁免；
  本 PR 已含完整版本目录（2.2.0/conanfile.py 等），CI 可正常定位并构建（不会 No packages to build），
  故用 OHC_PREFLIGHT=0 显式跳过（框架 R38↔PF9 冲突，逃生口自担风险）。
