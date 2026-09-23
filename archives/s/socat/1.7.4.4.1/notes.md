# socat 1.7.4.4.1 适配笔记

> **版本说明**：conan 引用版本 `1.7.4.4.1` 表示**基于上游 1.7.4.4 的 OHOS 适配轮次**
> （本仓惯例，如 gnupg `2.4.9.1`）。源码 URL 仍指向上游 `socat-1.7.4.4.tar.gz`，
> 交付产物自报版本亦为 `1.7.4.4`（上游版本号不因适配轮次改变）。

## 编译环境

- 构建系统: autotools（上游 release dist tarball，**自带 `configure`**，无需 autoreconf）
- 编译日期: 2026-09-20
- 编译器: clang 15（`/data/service/hnp/bin/clang`）
- 平台: HarmonyOS (HongMeng Kernel 1.12.0, aarch64)
- 状态: built

## 编译步骤

```bash
# 1. 取源码（release dist tarball，自带 configure）
#    http://www.dest-unreach.org/socat/download/socat-1.7.4.4.tar.gz
#    sha256 0f8f4b9d5c60b8c53d17b60d79ababc4a0f51b3bb6d2bd3ae8a6a4b9d68f195e

# 2. 应用 conandata 补丁（0001：移除 configure 中两处 umask 077）

# 3. 配置（不传 --build/--host，R1；另加两处头文件探测覆盖，见下）
./configure --prefix=/ \
    ac_cv_header_resolv_h=no \
    ac_cv_header_sys_stropts_h=no

# 4. 构建
make -j1        # E074：HMDFS jobserver fifo EPERM，须串行
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure` 中止：`config.status: error: could not setup config files machinery`（伴随 `can't create ./confXXXXXX/subs1.awk: Permission denied`） | `configure` 生成 `config.status` 时用 `(umask 077 && mktemp -d)` 建临时目录，HMDFS 强制目录 setgid 下 077 无法创建（同族 E114） | 补丁 `0001` 移除两处 `umask 077` |
| 2 | 编译失败：`xio-ip.c:119:11: error: use of undeclared identifier '_res'` | OHOS sysroot **有** `<resolv.h>`，但 libc **不导出全局 `_res`**（也无 `__res_state()` 访问器）。socat `configure.ac:79` 的 `AC_HEADER_RESOLV()` 只判断头文件存在 → `HAVE_RESOLV_H=1` → `#if HAVE_RESOLV_H` 段使用 `_res.options` | `ac_cv_header_resolv_h=no` → `HAVE_RESOLV_H` 不定义 → 跳过整段（该段只提供已废弃的 resolver 调优选项；域名解析仍由 `getaddrinfo()` 提供）。**同族知识条目 E516** |
| 3 | 链接失败：`ld.lld: error: undefined symbol: isastream` | OHOS sysroot 有 `<sys/stropts.h>`（内容仅 `#include <stropts.h>`），而 `<stropts.h>` **定义了 `I_LIST`**，使 `filan.c:452` 的 `#ifdef I_LIST` 块激活并调用 `isastream()`；但 libc 不声明也不导出该函数 | `ac_cv_header_sys_stropts_h=no` → 不引入该头 → `I_LIST` 未定义 → 整段跳过（该块为 SunOS STREAMS 遗留，与核心中继功能无关） |

### 对照实验（避免误修）

- `--disable-res-deprecated` **无效**：它只关 `WITH_RES_DEPRECATED`，不关 `HAVE_RESOLV_H`，`_res` 仍被引用（实测仍编译失败）。

## 源码修改

`patches/0001-configure-drop-umask-077.patch`

```diff
--- a/configure
+++ b/configure
@@ -22138,12 +22138,12 @@
 # Create a (secure) tmp directory for tmp files.

 {
-  tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&
+  tmp=`mktemp -d "./confXXXXXX" 2>/dev/null` &&
   test -d "$tmp"
 }  ||
 {
   tmp=./conf$$-$RANDOM
-  (umask 077 && mkdir "$tmp")
+  mkdir "$tmp"
 } || as_fn_error $? "cannot create a temporary directory in ." "$LINENO" 5
 ac_tmp=$tmp
```

仅改 `configure` 的临时目录 umask；**未触碰任何 `.c`/`.h` 源码**。

> 两处 `ac_cv_header_*` 修法通过 configure 命令行传入，不落为补丁（无需改源码）。

## 依赖版本

本包**无库依赖**（仅 libc）；构建期不需要额外工具（自带 configure，无需 autoreconf）。

## 验证结果

```bash
conan create archives/s/socat/1.7.4.4.1 --version=1.7.4.4.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# → EXIT=0

# 产物可执行性（构建通过 ≠ 产物可用）
socat -V
# → socat version 1.7.4.4 on Sep 20 2026 ... machine aarch64

# 功能实测
socat -u "exec:echo HELLO_SOCAT" -
# → HELLO_SOCAT
```

`test_package` 实测：**RESULT: PASS (6 checks, 0 failures)**
（含 `socat -V`、`socat -h`、单向中继、**TCP 中继**、`filan`、`procan`）

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/socat` | 主程序（中继） |
| `bin/filan` | 文件描述符分析工具 |
| `bin/procan` | 进程/地址分析工具 |

三者均含 `.codesign` 段且实测可执行（`.codesign` 计数均为 1）。

## 注意事项

- **上游仅提供 http**（无 https 端点）：`conandata.yml` 按上游实际写 `http://`。
- **无需 `config.guess`/`config.sub` 补丁**：本包自带 `configure`，且 `configure.ac` 内 `AC_CANONICAL_*` 命中为 **0**，configure **不调用** `config.guess`。
- **上游测试未执行**：`test.sh` 需完整外部对端（openssl/代理/TCP/UDP/UNIX socket）与长时间运行，不属包构建职责。如实申报，未以 skip/xfail 掩盖。
- `test_package` 的 TCP 断言采用「重试发送 + 轮询内容到达」：本环境 `/dev/tcp` 就绪探测不可靠（实测连续失败但转发成功），故避免竞态假失败；断言强度未降低。

---

**编译结束**: 2026-09-20
**最终状态**: built
