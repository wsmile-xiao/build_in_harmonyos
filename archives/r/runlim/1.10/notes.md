# runlim 1.10 适配笔记

## 编译环境
- 构建系统: makefile（上游极简 POSIX：`configure.sh` 将 `$CC/$CFLAGS` 代入 `makefile.in` 生成 `makefile`，单次编译器调用）
- 编译日期: 2026-09-20
- 编译器: OHOS SDK clang 15.0.4（`~/.harmonybrew/opt/ohos-sdk@26.0.0.18/native/llvm/bin`）
- 目标平台: HarmonyOS PC / aarch64-linux-ohos（HongMeng Kernel 1.12.0，HAD-W32）
- 上游源码: <https://fmv.jku.at/runlim/runlim-1.10.tar.gz>
  - sha256 = `619aec701e9984977832e2db2bf05cef82ad6ac4ca53b595863bec115b69bc33`（下载后实测校验一致）

## 编译步骤
1. `get()` 下载官方 tarball；`apply_conandata_patches()` 应用 1 个补丁（RLIMIT_AS 单位修复）
2. `build()`：以 Conan conf 的 clang 作为 `$CC`、`-O2 -DNDEBUG` 作为 `$CFLAGS`，执行 `configure.sh` 生成 makefile（R33/R5），再 `make -j1`（R9）单次编译产出 `runlim`
3. 上游无 install 目标：`package()` 直接拷贝 `runlim` → `bin/`、`LICENSE` → `licenses/`
4. `conan create` 内 test_package：`test_runlim.sh` 31/31 PASS（见 reports/test-report.md）

## 上游测试清点（R51 申报表）

| 检查项 | 命令 | 结果 |
|---|---|---|
| tests/ 目录 | 解压树（.orig，8 个文件） | 无 tests/test/Test 目录 |
| 测试源文件 | `find . -iname '*test*' -o -iname '*check*'` | 无结果 |
| makefile 测试目标 | `cat makefile.in`（全文 5 行） | 仅 runlim/clean 两目标，无 check/test |
| configure 测试开关 | `cat configure.sh`（全文 43 行） | 仅 -h/--help/-g，无测试开关 |
| 实测运行 | `sh configure.sh && make check`（scratch 副本） | `make: *** No rule to make target 'check'`（上游 0 用例） |

**结论：上游 1.10 不含任何测试套件（N=0，附上表清点证据）。按 R51，由 `test_package/test_runlim.sh` 补 31 条消费侧功能断言（真实执行已安装二进制，见 MANIFEST.yml）。**

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `runlim -t 1 sh -c ...` 恒报 `status: execvp failed`（rc=1），而 `-r`/默认路径正常 | runlim.c 将 `space_limit`（MB）原样赋给 `RLIMIT_AS`（内核单位字节）→ setrlimit 后子进程地址空间仅 ~31KB，`execvp` 失败 ENOMEM。`-t`（time_limit < real_time_limit）才触发该 setrlimit 块 | 补丁 0001：`((rlim_t) space_limit << 20)`（64 位强转防溢出）。最小复现（设备实测）：`setrlimit(RLIMIT_AS, 31914)` 后 `execv("/bin/echo")` → errno=12 ENOMEM；`31914<<20` → 正常执行 |
| 2 | 疑问：OHOS 的 `/proc/<pid>/stat` 布局是否与 Linux 一致（runlim 按固定字段索引解析） | 实测 HongMeng Kernel 1.12 的 stat 行：field 23=vsize（字节，与 VmSize 一致）、field 24=rss（页，与 statm resident 一致）、field 14/15=utime/stime（jiffies）——与标准 Linux 一致 | 无需适配；`-r 1` 实测 time=0.72s/real=1.03s 采样正确，`-s 1` 采样击杀 rc=3 |

## 源码修改

`patches/0001-runlim.c.patch`（+1/-1 行，纯单位修复，无平台宏，R8/PF5）：

```diff
-	l.rlim_cur = l.rlim_max = space_limit;
+	l.rlim_cur = l.rlim_max = ((rlim_t) space_limit << 20);
```

## 依赖版本

无。W0 依赖检查：`requires` 为空；源码仅 POSIX/libc 头文件，无 pkg-config/AC_CHECK_LIB 依赖。

## 验证结果

```text
# 设备手工构建（OHOS SDK clang 15.0.4，aarch64 原生）
$CC -Wall -O2 -DNDEBUG -DVERSION='"1.10"' -o runlim runlim.c   → rc=0
runlim --version → "1.10" rc=0

# 限制行为实测（修复后）
runlim -r 1 sh -c 'while :; do :; done'                  → rc=2 "out of time"（real 1.03s，samples 7）
runlim -t 1 sh -c 'i=0; while ... done'                  → rc=2 "out of time"（time 1.01s，samples 10）
runlim -s 1 <busy loop>                                  → rc=3 "out of memory"（space 9.1 MB）
runlim sh -c 'kill -11 $$'                               → rc=4 "segmentation fault"
runlim -k sh -c 'kill -11 $$'                            → 自身被信号 11 终止（shell 139）
runlim sh -c 'exit 42'                                   → rc=0（子进程退出码被忽略，status ok）

# 修复前基线（同一源码，仅未打补丁）
runlim -t 1 sh -c '...'                                  → rc=1 "execvp failed"（回归用例依据）

# conan create 内 test_package（conan-verify G2 / finish W3）
1..31
# passed: 31, failed: 0
conan-verify：G0–G4 全 PASS（reports/conan-verify-report.md）
本地 CI 门禁：L0/L1/L1e/L2/L4/L5 PASS，.ci-result.json exit_code=0（L1e 破坏性反向验证确认测试真实依赖 runlim）
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/runlim | 主程序（aarch64 ELF） |
| licenses/LICENSE | 上游 BSD-4-Clause 许可 |

## 注意事项

- 产物为可执行命令，已在软件级 `archives/r/runlim/commands.json` 声明（R38）。
- 退出码语义：runlim 返回自身状态（0/1/2/3/4/5/6/7/11），**不转发子进程退出码**（上游设计）。
- 需要 Linux/OHOS 风格 `/proc`；无 `/proc` 的环境不可用（上游设计）。

---

**编译结束**: 2026-09-20 21:05
**最终状态**: built
