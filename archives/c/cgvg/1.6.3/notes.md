# cgvg 1.6.3 适配笔记

## 编译环境
- 构建系统: custom（直接文件安装，等价替换 autotools 的 configure 处理；上游 autotools 壳仅做 @PERL@ shebang/@VERSION@/@datadir@ 替换 + 安装）
- 编译日期: 2026-09-07
- 编译器: N/A（纯 Perl 脚本包，无 C/C++ 源码，无编译步骤）
- 状态: built
- 分支: feat/cgvg-1.6.3

## 背景与语言判定（用户决策，覆盖 R47）
cgvg 1.6.3 为纯 Perl 脚本工具对（cg/vg 两个脚本 + cgvg-common.pl + man page），
autotools 壳只是"生成脚本+安装"，无任何 .c/.h/.cpp。lang-preflight 按 R47 判定
task=cpp / detected=mixed（manifest=autotools、源码统计 perl 100%），exit 2 自动写
env_unsupported 终态（本任务 result 落盘于 OHC_RESULT_OUT 私有路径，证据留档）。
**用户决策：此类脚本包按仓库既有"脚本包正常适配先例"（alot/check-jsonschema，
conan 打包 + wrapper/test_package 冒烟，status=built）走完整适配流程**——本任务
按此继续执行，最终结果覆盖语言闸上报。

## 编译步骤

1. 探索：解压 `cgvg_1.6.3.orig.tar.gz`（sha256=d879f541abcc…a12f3，Debian pool
   pristine 原包，上游 uzix.org 已失效）。产物形态 = cg/vg 两个 perl 脚本
   （cg.in/vg.in 经 autoconf AC_OUTPUT 替换 `#!@PERL@`→实际 perl 路径、
   @VERSION@、@prefix@、`use lib dirname($0), "@datadir@/cgvg"` 后生成），
   数据 cgvg-common.pl/cgvgrc-example → share/cgvg，man page → man1。
2. OHOS perl 确认：`which perl` → `/data/service/hnp/bin/perl`（perl.org 5.42.0,
   built for aarch64-linux，系统预装）。版本检查 `exit ($] < 5)` 通过。
3. 配方（conanfile.py）采用**直接文件安装**（脚本包范式，最简单可靠）：
   - build()：对 cg.in/vg.in 做与 configure 等价的替换——`#!@PERL@` →
     `#!/usr/bin/env perl`（运行期按 PATH 解析 OHOS perl，包可重定位）；
     @VERSION@→1.6.3；去掉 @prefix@/@datadir@（数据文件装到脚本旁，
     上游脚本首个 @INC 项即 dirname($0)，语义兼容）；生成后 `perl -c` 语法
     校验（本机 2/2 syntax OK）。
   - package()：bin/cg、bin/vg（755）+ bin/cgvg-common.pl、bin/cgvgrc-example
     （数据随脚本，包内零绝对路径）；share/man/man1/cg.1、vg.1；licenses/COPYING。
   - 未跑 autotools configure 的原因：configure 会把构建机绝对 perl 路径和
     configure 期 --prefix datadir 烤进脚本 → Conan 包不可重定位；且 1.6.3
     发行 configure 为 autoconf 2.13 老脚本，无必要引入。
4. 测试（上游无测试套件，Makefile.am 无 TESTS/check_PROGRAMS，`make check`
   无可执行内容——如实记录）；test_package 做 R34 实质验证（test_cgvg.py，
   14 断言，OHOS perl 真实执行）：
   - `cg hello` 递归搜索 → rc=0，输出含 hello.c 与匹配行
   - `cg -l` 经 ~/.cglast 回放 → rc=0
   - `vg 0`（EDITOR=fakevi 假编辑器）→ FAKEVI-ARGS:+1 hello.c，验证日志→
     行号→编辑器链路；vg 无参错误路径 rc≠0
5. conan create（-pr ohos-aarch64）→ PASS；conan-verify 8 门禁 → PASS。
   CI L1e 破坏性测试依赖 test_package 真实执行 cg/vg（sabotage bin/ 后必失败），
   已满足；CI L2 冒烟对 cg/vg 跑 --version/--help 会 warn（脚本无该选项，
   上游行为如此，L2 非阻断）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | R47 语言闸判定 mixed（perl 100%） | 脚本包无 C/C++ 主体 | 用户决策走脚本包适配先例，记录判定后继续（见上） |
| 2 | autotools 烤死绝对路径不可重定位 | configure 期替换 shebang/datadir | 直接安装 + `#!/usr/bin/env perl` + 数据文件与脚本同目录（上游首个 @INC 即 dirname($0)） |
| 3 | 上游无测试套件 | Makefile.am 无 TESTS | test_package 端到端功能冒烟（R34），14 断言全过 |

## 源码修改

无补丁（patches 空）。仅配方内做 configure 等价文本替换（见 conanfile.py
`_transform_script`）。

## 依赖版本

- 运行时: perl 5.42.0（OHOS PC 系统预装，/data/service/hnp/bin/perl）——
  不作为 conan 依赖打包（OHOS 无 perl Conan 包，系统自带即运行时）
- 构建期: 无（纯文件操作 + 可选 perl -c）

## 验证结果

```bash
# 探索期端到端（手动安装布局）
$ cg hello            # → "0 hello.c 1 hello world" rc=0
$ cg -l               # → 回放同一条目 rc=0
$ EDITOR=fakevi vg 0  # → "FAKEVI-ARGS:+1 hello.c" rc=0
$ perl -c cg; perl -c vg   # syntax OK ×2

# 配方验证
$ conan create archives/c/cgvg/1.6.3 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
  # PASS：source 下载+sha256 校验 → perl -c ×2 syntax OK → test_package
  # "cgvg-smoke PASS: ... verified end-to-end under /data/service/hnp/bin/perl"
$ ohc-run.py conan-verify cgvg 1.6.3   # G1-G4/L2/L4/L5 全 PASS
```

## 注意事项

- vg 启动时对 $EDITOR（默认 vi）做 `which` 检查：OHOS 无 vi 时需先 export
  EDITOR（vim/emacs/…），属上游行为，README 已注明。
- cg/vg 无 --version/--help 选项，CI L2 冒烟对这些脚本为 warn（非阻断）。
- 数据文件（cgvg-common.pl/cgvgrc-example）与脚本同目录是重定位所必需；
  如需按上游 share/cgvg 布局部署，等价于把数据拷到脚本同层目录。
- 上游发行 tarball 亦存于 https://waterlan.home.xs4all.nl/cgvg/（官方长期
  镜像）；本包取 Debian pool pristine 包并 sha256 钉死。
---

**编译结束**: 2026-09-07 11:08
**最终状态**: built
