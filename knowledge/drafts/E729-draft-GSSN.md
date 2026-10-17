# E729: autotools tag 归档新包在本设备 autoreconf 自举的 perl 双解释器陷阱

**Category**: build-system / autotools / perl / toolchain · **Severity**: high · **Tool**: autoreconf/aclocal/automake

## 症状

1. `autoreconf -f -i` 直接崩：
   `Can't load '…/perl5/5.42.2/…/auto/Cwd/Cwd.so': Error relocating …: Perl_my_cxt_init: symbol not found`
   （报错落点在 `/data/service/hnp/bin/autoreconf line 48` 或 `.aclocal-real line 31`）。
2. 换成显式 conan 入口后又出：`.aclocal-real: error: couldn't open directory '//share/aclocal-1.18'`。
3. 修 PATH 后依旧命中 HNP 工具：`autoreconf` 经 `$ACLOCAL/$AUTOMAKE` 环境变量按**绝对路径**
   调用，绕过一切 PATH shim。

## 根因（四层叠加，缺一即崩）

1. **两套 perl 的 XS ABI 互不兼容**：HNP `perl 5.42.0`（非 i-thread，无 `Perl_my_cxt_init` 符号）
   vs conan `perl 5.42.2`（`aarch64-linux-thread-multi`）。谁也加载不了谁的 `.so`，
   PERL5LIB 指错方向必崩。
2. **shebang 与 PERL5LIB 自相矛盾**：ohpcd `automake/1.18` 的 `.aclocal-real/.automake-real`
   shebang 写死 `#!/data/service/hnp/bin/perl`，而 conanbuild 的 PERL5LIB 又指向 conan perl——
   两者不可调和；反过来 conan autoconf 系 `.real` 的 shebang 是 conan perl，其 `@INC` 编译前缀
   还是坏的 `//lib/perl5/…`（`--prefix=/` 家族），脱离 PERL5LIB 连 `Cwd` 都找不到。
3. **PATH 优先级**：conanbuildenv 把 `/data/service/hnp/bin` 排在 tool_requires 之前，
   裸调 `autoreconf` 必中 HNP；且改 `os.environ` 无效——conanbuild 环境脚本会把 profile 路径
   **重新压到最前**（实测）。
4. **重定位参数被绕过**：shim 若直接 `exec perl .aclocal-real`，会丢掉 ohpcd 包装脚本提供的
   `--automake-acdir/--system-acdir/--libdir`（`.real` 编译进的前缀是 `//share/…`）；
   且 `autoreconf` 走 `$ACLOCAL` 绝对路径时 PATH shim 根本不生效。

## 处置（可复用：`autoreconf-perl-unify-shim` 四件套）

1. `build_requirements()` 同源拉齐 `autoconf/2.72 + automake/1.18 + libtool/2.5.4`
   （CI worker 无 automake/libtool，device-facts §一.4；三者连同 perl/m4 全部来自 conan 才能与
   PERL5LIB 同族）。
2. `build()` 内把 tool_requires 各包 `bin/` 前置到 PATH；`autoreconf` 调用再加**命令行内联
   PATH 前缀**（覆盖 conanbuild 的重排）。
3. 生成 `aclocal`/`automake` shim：`exec <conan-perl> <pkg>/bin/.<name>-real` + **复刻重定位参数**
   （`--automake-acdir=<pkg>/share/aclocal-1.18 --system-acdir=<pkg>/share/aclocal`、
   `--libdir=<pkg>/share/automake-1.18`），shim 目录置于 PATH 首位。
4. autoreconf 调用加 `ACLOCAL=<shim> AUTOMAKE=<shim>` 内联变量（防 `$ACLOCAL` 绝对路径绕过）。

自检三行（gss-ntlmssp 实测日志）：

```sh
grep -a '\[shim\] 2 perl shims' "$HOME/tmp/gss-ntlmssp-1.2.0/local-create-14.log"
grep -ac 'RUN: ACLOCAL=.*_perlshim/aclocal AUTOMAKE=.*_perlshim/automake' "$HOME/tmp/gss-ntlmssp-1.2.0/local-create-14.log"
grep -ac 'Perl_my_cxt_init' "$HOME/tmp/gss-ntlmssp-1.2.0/local-create-14.log"   # 期望 0
```

## 复现（设备可直接执行）

```sh
CP=$(find "$HOME/.conan2/p" -maxdepth 1 -type d -name 'perl*' | head -1)
/data/service/hnp/bin/perl -I "$CP/lib/perl5/5.42.2" -MCwd -e1   # 预期崩: Perl_my_cxt_init
"$CP/bin/perl" -I "$CP/lib/perl5/5.42.2" -MCwd -e1 && echo OK    # conan perl 正常
```

## 定位链（gss-ntlmssp 1.2.0，2026-09-25）

`local-create-1`（HNP autoreconf 崩）→ `create-3`（inline PATH 仍被 conanbuild 重排覆盖）
→ `create-4`（shim 生效但缺重定位参数，`//share/aclocal-1.18`）→ `create-5/6`（补
`$ACLOCAL/$AUTOMAKE` 内联）→ `create-6` 起 autoreconf 全绿（仅 `AC_ERROR is obsolete` 警告）。

与 device-facts §一.23（conan autoconf PERL5LIB 毒丸）互补：那条给了"显式 tool_requires"，
本条补齐另一半——**PATH 优先级 + shebang 统一 + 重定位参数 + `$ACLOCAL` 绝对路径**。
