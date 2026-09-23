# castget 2.0.1 适配笔记

## 编译环境
- 构建系统: autotools（GitHub tag archive 无预生成 configure，需 autoreconf -fi 自举）
- 编译日期: 2026-09-07
- 编译器: clang 15.0.4（OHOS SDK，/data/service/hnp/bin/clang）
- 设备: HarmonyOS PC aarch64（真机），CONAN_HOME=~/tmp/ch/home-castget
- 状态: built

## 上游与源码
- 上游仓库: https://github.com/mlj/castget
- 上游版本: 2.0.1（tag rel_2_0_1）
- 源码: https://github.com/mlj/castget/archive/refs/tags/rel_2_0_1.tar.gz
- SHA256: 8cefeb8c76daa791953ee1a555473cc83a29a2d18a29adeb2aef7a41e2212f49
- 语言: C（lang-preflight：c↔cpp 兼容族，通过）

## 构建配置
- 三元组: --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu
  （自举的 config.guess 不认识 HarmonyOS，按 blogc/authselect 同款方案）
- 依赖: glib/2.84.0.1、libxml2/2.15.3.1、curl/8.15.0（PkgConfigDeps + curl-config wrapper）
- zlib 版本对齐: curl 对 zlib/1.3.1.1 force 固定，glib/2.88 系要 1.3.2 → 换用
  glib/2.84.0.1（zlib 用系统库不进图）+ requires("zlib/1.3.1.1", override=True) 对齐
- id3lib: --disable-id3lib 关闭（制品仓无该包，非核心功能）
- man 页: tarball 只有 .ronn 源，构建前 touch 最小占位 .1/.5 文件绕开 ronn 依赖

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 working directory cannot be determined | HNP bash getcwd 在 HMDFS 失败（同 blogc，配方 _pick_working_shell 实测探测修复） | 探测候选 shell 覆盖 SHELL/CONFIG_SHELL |
| 2 | mksh 写 /tmp 失败：can't create temporary file /tmp/shXXX.tmp: Read-only file system（CI worker 与当前设备整平台 /tmp 只读） | CI worker 上 bash 不在 PATH，探测回退 /bin/sh=mksh；mksh 临时文件硬编码 /tmp 无视 TMPDIR | tool_requires("bash/5.3")（制品仓），探测优先用 build 上下文 bash；configure/make check 显式用该 bash 执行 |
| 3 | autoreconf 需要 pkg.m4（PKG_CHECK_MODULES 未展开 → configure syntax error） | tag archive 无 m4/ 目录 | source() 里把设备 pkg-config 的 pkg.m4 复制进 m4/ 再 autoreconf |
| 4 | autoreconf OOM（autom4te: Out of memory / can't fork） | 共享设备多任务并发内存压力 | source() 内 autoreconf 幂等重试（4 次，间隔 45s） |
| 5 | test_progress 运行即 SIGABRT（exit 134） | 测试用 tmpfile()，musl 硬编码 /tmp（只读）返回 NULL 后写崩 | 补丁 0001：改用 TMPDIR 下 mkstemp+fdopen（不改断言），g_assert(pb->f != NULL) 校验 |
| 6 | 补丁看似未应用（无 Apply patch 日志行） | conandata.yml 补丁键写成上游无关的 "0.20.1"（copy-paste 自 blogc），与 recipe version "2.0.1" 不匹配被静默忽略 | 键改 "2.0.1" 后正常应用 |
| 7 | check.log 无 "ok N" 行导致计数误判 0 | automake harness 把测试程序 TAP 输出重定向到 tests/<name>.log，不在顶层 check.log | _parse_check_results 从 tests/*.log 统计 ok 行数（9） |
| 8 | config.status subs1.awk Permission denied | HMDFS umask 077 组合（E011/E114） | 运行前把生成的 configure 内 umask 077 替换为 umask 022 |

## 上游测试（真实执行，数字与包内 res/upstream_test_result.json 同源）
- 上游 TESTS 注册条目: 3（tests/Makefile.am check_PROGRAMS = TESTS）
- GLib 框架注册用例（g_test_add_func 静态计数）: patterns 6 + progress 2 + filenames 1 = 9
- 实际执行: 3 条目 / 9 用例，全部通过；失败 0，跳过 0
- 运行方式: build() 里 make -k check，解析 automake 汇总 + tests/*.log 的 ok 行
- 汇总 JSON: {"total":3,"passed":3,"failed":0,"skipped":0,"g_test_cases_executed":9}
- test_package 消费者断言: 4/4（HMBS_TEST_PACKAGE_RESULT）

## 上游测试修改说明
- 唯一修改: 补丁 0001-tests-test_progress.c.patch
  （tests/test_progress.c：tmpfile() → mkstemp(TMPDIR)/fdopen，补 unistd.h；
  不改任何断言与测试逻辑）

## test_package
- test.sh 真实行为断言: castget -V 版本横幅；本地 file:// RSS 2.0 feed 经
  --list 全栈解析（libxml2+curl）；--catchup 完整运行；缺失 rcfile 错误路径。
  输出 HMBS_TEST_PACKAGE_RESULT 标记。
- 包内 res/upstream_test_result.json 由 build() 持久化，test_package 重发
  HMBS_UPSTREAM_TEST_RESULT（缓存复用时标记仍出现在每份日志）。

## 已知限制
1. 上游仅有 tests/ 三个单元套件，无更多测试目录；channel 下载主流程需
   网络，test_package 以本地 file:// feed 的 --list/--catchup 补足集成验证
2. id3lib 支持按 --disable-id3lib 关闭（制品仓无 id3lib 包）
---

**编译结束**: 2026-09-07 15:51
**最终状态**: built
