# retry 1.0.6 适配笔记

## 编译环境
- 构建系统: autotools（官方 release tarball 自带 configure / Makefile.in / config.h.in / build-aux / m4）
- 编译日期: 2026-09-18
- 编译器: OHOS SDK clang/clang++ 15.0.4（`~/.harmonybrew/opt/ohos-sdk@26.0.0.18/native/llvm/bin`）
- 目标平台: HarmonyOS PC / aarch64-unknown-linux-ohos（HongMeng Kernel 1.12.0，HAD-W32）
- 上游源码: <https://github.com/minfrin/retry/releases/download/retry-1.0.6/retry-1.0.6.tar.gz>
  - sha256 = `c208baf759134da27012042ccc30df7d995ed038d7d5602db7dbda3becb34827`（下载后实测校验一致）

## 编译步骤
1. `get()` 下载官方 release tarball；`apply_conandata_patches()` 应用 3 个可移植性补丁
2. `AutotoolsToolchain.generate()`；`autotools.configure()` → `autotools.make(args=["-j1"])`（R9）
3. `autotools.make(target="check")`：上游无测试套件，实测 0 用例（见下 R51 清点）
4. `autotools.install()` → `bin/retry`、`share/man/man1/retry.1`
5. `conan create` 内 test_package：`sh test_retry.sh` 28/28 PASS

## 上游测试清点（R51 申报表）

| 检查项 | 命令 | 结果 |
|---|---|---|
| tests/ 目录 | `find . -type d`（解压树） | 无 tests/test/Test 目录（.orig 共 28 个文件） |
| 测试源文件 | `find . -iname '*test*' -o -iname '*check*'` | 无结果 |
| automake 测试目标 | `grep -n 'TESTS\|check_PROGRAMS' Makefile.am` | 无（仅 `bin_PROGRAMS = retry`） |
| configure 测试开关 | `grep -c 'enable.*test' configure` | 0 |
| 实测运行 | `make check` | 退出码 0，执行 0 用例（automake 默认空目标） |

**结论：上游 1.0.6 不含任何测试套件（N=0，附上表清点证据）。按 R51，由 `test_package/test_retry.sh` 补 28 条消费侧功能断言（真实执行已安装二进制，见 MANIFEST.yml）。**

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: cannot guess build type; you must specify one` | 上游 2018 年版 config.guess 不认识 `uname -s = HarmonyOS`；native 构建（build==host）时 AutotoolsToolchain 不传 `--host/--build`，configure 必然走 config.guess | 补丁 0001：在 UNAME 三元组分派处增加 HarmonyOS 分支，输出 `aarch64-unknown-linux-ohos`（E007 家族，与 lrcalc 1.2 同一先例） |
| 2 | config.sub 无法 canonicalize `*-linux-ohos` | GNU config.sub（timestamp 2018-08-29）未收录 ohos：`maybe_os` 列表与大 OS 列表均无 `linux-ohos*`；且其 `linux*)` 兜底会把 `-linux-ohos` 误改写为 `-linux-gnu-ohos` | 补丁 0002：`maybe_os` 列表（三字段 `aarch64-linux-ohos`）与大 OS 列表（四字段 `linux-ohos`）各补 `linux-ohos*`（纯 POSIX 修复，无平台宏） |
| 3 | HMDFS 上 config.status 临时目录 Permission denied（E011） | configure 以 `umask 077 && mktemp -d ./confXXXXXX` 创建临时目录；HMDFS UID 映射（目录 owner 20001006 vs 进程 UID）使 0700 目录对构建进程不可写 | 补丁 0003：临时目录创建 umask 放宽为 022（与 aaphoto/lrcalc 同一已验证先例） |
| 4 | 自动化中调用 retry 会吞掉调用方的 stdin | retry 设计上把 stdin 捕获进内存并在重试时重放（README 明确说明） | 在 notes/README 中提示；test_package 中除 stdin 重放用例外全部显式 `</dev/null`，避免测试脚本自身 stdin 被吞（本次探针阶段实际踩到过：SSH 流式脚本被 retry 吞掉后半段） |

## 源码修改

`patches/` 三个补丁，全部为可移植性修复，均不注入平台宏（R8 / PF5）：

1. `0001-build-aux-config.guess.patch` — HarmonyOS → `aarch64-unknown-linux-ohos`（+3 行）
2. `0002-build-aux-config.sub.patch` — 接受 `linux-ohos`（两处列表，+2/-2 行）
3. `0003-configure.patch` — config.status 临时目录 umask 077→022（+2/-2 行）

## 依赖版本

无。W0 依赖检查：`requires` 为空；configure.ac 无 `AC_CHECK_LIB`/pkg-config 依赖，仅链接系统 libc。

## 验证结果

```text
# 本机手工构建（OHOS SDK clang 15.0.4，aarch64 设备原生）
configure rc=0 → make rc=0 → make check rc=0（0 用例）
./configure --prefix=$DEFAULT_PREFIX && make -j1 && make install DESTDIR=$TEST_PREFIX
产物: bin/retry (ELF aarch64), share/man/man1/retry.1

# 手工功能验证（安装产物直接执行）
retry --version → "retry 1.0.6" rc=0
retry -d 0 -t 5 --until=success  第 3 次成功，attempts=3，rc=0；失败尝试 stdout 转入 stderr
retry -d 0 -t 2 -- false → rc=1，stderr "giving up."
retry -d 0 -t 1 -- sh -c 'exit 42' → rc=42（退出码透传）
printf 'alpha\nbravo\n' | retry -d 0 -t 3 -- sh stdin_probe.sh（首试失败、二试成功）
→ 两次尝试都收到完整 stdin（捕获并重放），rc=0

# test_package（sh test_retry.sh）
28/28 PASS（见 test_package/MANIFEST.yml；conan create 日志与 reports/test-report.md）
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/retry | 主程序（aarch64 ELF） |
| share/man/man1/retry.1 | man 手册（上游发行包内已生成，无需 txt2man） |

## 注意事项

- 产物为可执行命令，已在软件级 `archives/r/retry/commands.json` 声明（R38）。
- 退出码语义：返回被重复命令最后一次的退出码；无法执行/参数非法返回 1；被信号中断返回 128+signal。
- 管道中使用时 stdin 会被捕获并重放：在自动化脚本里调用请按需 `</dev/null`，需要透传输入时直接接管道即可（上游设计行为）。
---

**编译结束**: 2026-09-18 16:50
**最终状态**: built
