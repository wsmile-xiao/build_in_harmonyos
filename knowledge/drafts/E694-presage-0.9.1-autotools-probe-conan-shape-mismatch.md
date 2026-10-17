# E694 人类可读文档 — 上游 autotools 探测宏 vs Conan 包交付物形态失配（静默降级/假绿）

> 配对 kv：`knowledge/drafts/E694-presage-0.9.1-autotools-probe-conan-shape-mismatch.kv`
> 实证任务：presage 0.9.1（任务卡 9711，`feat/presage-0.9.1`，2026-09-24）

## 一句话

上游 configure 用「按程序名 / 按库基名」的探测宏，而 Conan 包交付形态不同（无
`cppunit-config` 程序、无 `libcurses.a` 基名）→ 探测失败走上游可选分支 →
**测试不构建、工具不构建，全程零报错**，`make check` 照样绿。

## 实证 1：AM_PATH_CPPUNIT 吞掉 94 个单测（假绿面）

presage `m4/cppunit.m4`（cppunit 老式 config-tool 约定）：

```sh
AC_PATH_PROG(CPPUNIT_CONFIG, cppunit-config, no)
CPPUNIT_CFLAGS=`$CPPUNIT_CONFIG --cflags`
CPPUNIT_LIBS=`$CPPUNIT_CONFIG --libs`
cppunit_version=`$CPPUNIT_CONFIG --version`
```

conan `cppunit/1.15.1` 包 `bin/` 只有 `DllPlugInTester`。没有该程序时：

`no_cppunit=yes` → `AM_CONDITIONAL([HAVE_CPPUNIT], ...)` 空 → `test/` 下
`check_PROGRAMS = testRunner`（及 6 个同族 runner）全部不构建 → `TESTS` 空
→ `make check` 直接通过。**94 个 `CPPUNIT_TEST` 一个都没跑。**

configure 日志会出现（可作 prescan 模式）：

```
checking for Cppunit - version >= 1.9.6... no
configure: WARNING: CppUnit not found. Unit tests will not be built. ...
```

同族先例：taglib 的 `FindCppUnit.cmake` 需要 `cppunit-config` 才设
`CPPUNIT_INSTALLED_VERSION`（cmake 形态，taglib 用变量注入解决）。

### 修法（recipe 层 shim）

`generate()` 在 buildfolder 写 `conan-shims/cppunit-config`：

```sh
#!/bin/sh
case "$1" in
  --cflags)  echo "-I<cppunit包>/include" ;;
  --libs)    echo "-L<cppunit包>/lib -lcppunit" ;;
  *)         echo "1.15.1" ;;
esac
```

`chmod 0755`，`env.prepend_path("PATH", shim_dir)`。

### 判据（修复前后都可用）

```sh
# 修复前（命中即降级发生）
grep -n "checking for Cppunit - version >= 1.9.6\.\.\. no" <build>/config.log
# 修复后
grep -n "checking for Cppunit - version >= 1.9.6\.\.\. 1.15.1" <build>/config.log
grep -c "^OK (" make-check.log   # 应等于 runner 数，且 OK 内用例和 == 有效注册宏数
```

设备复现（presage 实例）：

```sh
grep -n "AC_PATH_PROG(CPPUNIT_CONFIG" "$HOME/ws/tmp/builds/presage-0.9.1.work/m4/cppunit.m4"
ls "$(conan cache path cppunit/1.15.1:f23d5a9b1d537641c03c7814478a2fadb727650a)/bin"
```

## 实证 2：AC_CHECK_LIB([curses]) 吞掉 presage_demo（静默降级）

`AC_CHECK_LIB([curses],[initscr])` 按基名 `-lcurses` 链接；conan `ncurses/6.6`
只交付 `libncursesw.a`/`libmenuw.a` 等 *w 名，设备系统侧无 libcurses →
`have_curses_library` 空 → `AM_CONDITIONAL([HAVE_CURSES])` 空 →
`presage_demo`（bin_PROGRAMS 的可选成员）不构建，只有一行
`WARNING: curses library not found. curses demo programs will not be built.`

### 修法

`conan-shims/libcurses.a → <ncurses包>/lib/libncursesw.a` 符号链接；
`LIBRARY_PATH` 前置（clang 探针 rc=0 实证）+ `tc.extra_ldflags` 追加 `-L<shim>`
双通道注入（避开 conanautotoolsdeps 与自定义 env 脚本的 LDFLAGS 覆盖顺序不确定性）。

## 禁用做法

用 `CPPUNIT_CFLAGS=" " / CPPUNIT_LIBS=" "` 环境把探测顶掉（librevenge 的做法）
**只适用于不跑上游单测的包**；对 presage 这种测试面即核心资产的包，顶掉等于
主动放弃测试面 → 假绿红线。

## 推广形态

凡「上游按可执行程序名 / 库基名探测」+「conan 交付形态不同」的组合都要过一遍：
先 `grep` 上游 m4/Makefile.am 的探测宏，再 `ls` conan 包 `bin/`/`lib/` 实物对表，
不匹配就在 generate() 里补 shim 或注入变量——**探测失败不会报错，只会静默降级**。
