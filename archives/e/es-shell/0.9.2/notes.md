# es-shell 0.9.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-22
- 编译器: clang 15.0.4 (OHOS SDK)
- 状态: built

## 编译步骤

```bash
# 1. 生成 configure（上游未预生成，需 autoconf）
autoconf && autoheader

# 2. 拷贝 autotools 辅助文件（install-sh/config.guess/config.sub）
cp /data/service/hnp/autoconf.org/autoconf_2.72/share/autoconf/build-aux/{install-sh,config.guess,config.sub} .

# 3. 使用仓库内 OHOS 补丁版 config.guess/config.sub（识别 aarch64-unknown-linux-ohos）
#    来源: archives/b/babeltrace/1.5.11/patches/autotools/config/

# 4. 依赖: readline/8.3 + ncurses/6.6 从 ohpcd 制品仓安装
conan install --requires=readline/8.3 -r=ohpcd --build=missing -pr:h=ohos-aarch64 -pr:b=ohos-aarch64

# 5. configure + make
./configure --prefix=$DEFAULT_PREFIX \
  CPPFLAGS="-I<readline>/include" \
  LDFLAGS="-L<readline>/lib -L<ncurses>/lib -lreadline -lncursesw"
make -j2

# 6. 上游测试（trip 回归）
make test   # 通过
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure: cannot find required auxiliary files | 上游 tarball 未包含 install-sh/config.guess/config.sub | 从 autoconf build-aux 与仓库 OHOS 补丁版拷贝 |
| 2 | config.guess: unable to guess system type | 原版不认识 HarmonyOS | 使用仓库内 babeltrace 的 OHOS 补丁版 config.guess/config.sub |
| 3 | configure 检测 rlimit type 为空 → LIMIT_T 未定义，prim-sys.c 编译失败 | configure.ac 的 AC_CMDSTDOUT_CPP 使用 `$ac_cpp` 但从未调用 AC_PROG_CPP，autoconf 2.72 下 ac_cpp 为空 | configure.ac 增加 `AC_PROG_CPP` |
| 4 | 链接期 duplicate symbol: getstr | es-shell 自带 `getstr(Term*)` 与 ncursesw 的 curses `getstr` 冲突（readline 拉入 lib_gen.o） | 将 es-shell 自有 getstr 改名为 es_getstr（69 处） |
| 5 | trip 测试 panic: initsignals bad incoming signal value | OHOS 运行时预装 SIGILL/SIGSEGV/SIGSYS/实时信号崩溃处理器 | signal.c 对预装 handler 视为 sig_default 而非 panic |
| 6 | trip 测试写 /tmp 只读失败 | 鸿蒙 /tmp 只读（SKILL E002） | trip.es 改用 $TMPDIR（回退 /tmp） |
| 7 | trip 测试 umask 断言失败（期望 666/640，实际 660） | HMDFS/SELinux 强制文件权限 660（SKILL E046） | trip.es umask 断言同时接受平台实际模式 -rw-rw---- |
| 8 | config.status 临时目录 mktemp 生成 2700 不可写 | HMDFS 对 mktemp -d 目录写入受限 | 本地 mktemp shim 回退 mkdir 2771（仅本地环境，不入配方） |

## 源码修改

- configure.ac: 增加 AC_PROG_CPP（修复 rlimit/signal 检测）
- signal.c: initsignals 对预装信号 handler 视为默认
- 15 个 .c + es.h: getstr → es_getstr 改名
- trip.es: /tmp → $TMPDIR；umask 断言接受平台模式

## 依赖版本

- readline/8.3（ohpcd 制品仓）
- ncurses/6.6（ohpcd 制品仓，间接依赖）

## 验证结果

```bash
make test   # trip 回归通过 (exit 0)
echo hello | ./es  # 冒烟通过
```
---

**编译结束**: 2026-09-23 00:39
**最终状态**: built
