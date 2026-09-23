# cssc 1.4.1 适配笔记（HarmonyOS PC / aarch64-linux-ohos）

## 编译环境
- 构建系统: autotools（configure + make，老式 2016 config.guess/config.sub）
- 编译日期: 2026-09-11
- 编译器: clang 15.0.4 / clang++（OHOS SDK 26.0.0.18 sysroot）
- 上游: GNU CSSC 1.4.1（GNU Savannah，SCCS 兼容源码版本控制工具，C++98 老代码）
- 状态: published

## 编译步骤
```bash
export CC=clang CXX=clang++ CFLAGS="-O2" CXXFLAGS="-O2"
./configure --prefix=<prefix> --enable-static --disable-shared
make -j8
make install DESTDIR=<staging>
```
无外部 conan 依赖（自带 gnulib + 捆绑 googletest 1.6）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure: unable to guess system type | 2016 版 config.guess 无 HarmonyOS 分支 | config.guess 加 `*:HarmonyOS:*:*` 分支（echo+exit 0 风格，老版无 GUESS 变量机制） |
| 2 | config.sub 拒绝 aarch64-unknown-linux-ohos | 无 linux-ohos 三元组 | maybe_os 列表加 `linux-ohos*`；基础 OS 列表加 `-linux-ohos*` |
| 3 | 首次 configure 后 gl/lib 头文件 `#include ""` 空文件名错误 | 首轮 include_next 检测因瞬态 conftest 丢失失败→NEXT_AS_FIRST_DIRECTIVE 空；重跑 configure 后 Makefile 未刷新 | 重跑 configure 成功（检测通过）+ 删除陈旧生成头重新 make |
| 4 | `admin: UID 20020182 not found in password file` + SIGTRAP(133)，全部命令不可用 | OHOS 应用 UID 无 /etc/passwd 条目，getpwuid()=NULL，get_user_name() fatal_quit | src/file.cc get_user_name() 无条件回退 getenv("USER")/"unknown"（与非 CONFIG_UIDS 分支一致；R8 不用平台宏） |
| 5 | `sccs unedit: Who are you?` exit 71 | sccs.c username() 同样的 getpwuid NULL 问题 | sccs.c username() 同样加 __OHOS__ 回退 |
| 6 | `Could not create temporary file` (bodyio.cc) / `cannot create temporary file` (sccs.c) exit 71 | tmpfile() 用 P_tmpdir(/tmp)，OHOS /tmp 只读 errno=EACCES | 两处 tmpfile() 失败后回退 mkstemp(${TMPDIR})+fdopen("w+b")+unlink |
| 7 | unit-tests 4 个死亡测试 test_* 整体 abort(134) | 捆绑 googletest 1.6 CapturedStream 硬编码 `/tmp/captured_stream.XXXXXX`，mkstemp 失败→GTEST_CHECK abort 父进程 | gtest-port.cc 无条件改用 $TMPDIR（回退 /tmp，R8） |
| 8 | test_linebuf abort(134) | 测试自身 tmpfile() /tmp 失败 | test_linebuf.cc 加 make_temp_file() 助手（无条件 TMPDIR 回退 + fd 泄漏防护） |
| 9 | `not-root: can't create /tmp/foo.NNN.tmp: Read-only` | 测试脚本硬编码 /tmp | not-root/delsfile/compare_gets 改 ${TMPDIR:-/tmp} |
| 10 | `subst.sh %A%: stderr format error with egrep` | GNU grep 3.12 的 egrep 弃用警告打到 stderr，docommand 严格比对 stderr | subst/comment/2comment/4order 的 egrep→grep -E |
| 11 | `prs: s.y2k.txt had a hard link count which is greater than one` | SCCS 安全特性拒绝 nlink>1 的 s-file；init-build 的 .work 是 .orig 硬链接 farm | 探索时断链（cp 经 temp 中转）；此为测试环境问题非源码缺陷，conan 构建从 tarball 解压天然无硬链，无需补丁 |
| 12 | `gzip: not gzip`（prt/all-512.sh） | 上游 fixture all.expected.Z 是 compress(1) LZW 格式，gzip 不支持且 OHOS 无 ncompress | decompress_stdin.sh.in 改 exec python3（gzip 优先→纯标准库 LZW 回退，无第三方依赖，输出与 unlzw3 逐字节一致） |
| 13 | gl/tests test-fcntl: assertion errno==EINVAL failed | OHOS musl F_DUPFD 对非法第三参返回 ENOSPC/其他 errno 而非 EINVAL——平台 libc 行为差异 | 平台差异豁免（gnulib 自测试非 CSSC 功能测试，1/59） |

## 源码修改（16 个补丁）
见 manifest.yaml patches_applied。核心分类：
- 平台重锚：config.guess / config.sub
- UID 数据库缺失：src/file.cc / src/sccs.c（无条件 $USER 回退）
- /tmp 只读：src/bodyio.cc / src/sccs.c / gtest-port.cc / test_linebuf.cc / not-root / delsfile / compare_gets（无条件 $TMPDIR 回退；tmpfile 助手含 fd 泄漏防护）
- sccsdiff 工具查找+TMPDIR：src/sccsdiff.sh.in
- LZW 解压：testutils/decompress_stdin.sh.in
- egrep 弃用：subst.sh / comment.sh / 2comment.sh / 4order.sh

## 依赖版本
- 无 conan 依赖（零 requires）
- 运行时 libc++_shared.so 由 OHOS 系统提供

## 验证结果

```bash
# tests/ 上游测试套（Makefile.am 注册 17 个 test-* 目标，共 91 个 .sh 脚本）
$ USER=tester make -C tests check
Tests passed.        # rc=0
# 91 脚本全部执行：82 PASS + 1 XPASS + 8 以 cleanup/exit-0 收尾；0 FAIL
# 子断言约 1243 个 passed

# unit-tests（googletest）
$ make -C unit-tests check
# TOTAL: 11, PASS: 11, FAIL: 0, ERROR: 0

# gl/tests（gnulib 自测试，非 CSSC 功能）
# TOTAL: 59, PASS: 57, SKIP: 1(vc-list-files-cvs), FAIL: 1(test-fcntl 平台 errno 差异)

# staging 冒烟
$ sccs --version     # "from GNU CSSC 1.4.1"
$ admin -ifoo.txt s.foo.txt && get -p s.foo.txt   # round-trip OK
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/sccs | SCCS 前端命令 |
| libexec/cssc/{admin,get,delta,prs,prt,unget,sact,cdc,rmdel,val,what,sccsdiff} | 12 个 SCCS 工具 |
| share/man/man1/sccs.1, share/info/cssc.info | 文档 |

## 注意事项
- `sccs` 前端在编译期固化 csscutildir 前缀，包装器找 `$(csscutildir)/get`；test_package 通过 PATH+USER 驱动
- 死亡测试在纯 gtest 环境验证过：fork/pipe/abort 本身正常，根因是 CapturedStream 的 /tmp
- 依赖池满编件：本包为依赖池第 15/15 个（最后一位）
