# fontopia 2.0 适配笔记（HarmonyOS PC · GNU Autotools 控制台字体编辑器）

## 定位
- 产出 CLI/TUI 工具 `bin/fontopia`（GNU Fontopia：ncurses 控制台字体编辑器，`package_type = "application"`）。
- 上游基于 **GnuDOS 控制台库**（`libgnudos`）：`configure.ac` 硬检查 `console/dialogs.h|kbd.h|screen.h`，
  `Makefile.am` 链接 `-lgnudos`；ncurses 是 gnudos 的下游依赖。

## 编译环境
- 构建系统: autotools（release tarball 自带 configure）
- 编译日期: 2026-09-21
- 编译器: clang 15（aarch64-unknown-linux-ohos）
- CONAN_HOME: `~/tmp/ch/home-ds4-fontopia`
- 状态: built

## 源码
- https://ftp.gnu.org/gnu/fontopia/fontopia-2.0.tar.gz
- sha256: `0daa54bb1153f6108661e619f9b5e717f6c1e2385b25fc3a5135d4f64e5b6773`（真机下载实测）

## W0/W0b
- 依赖核验：`gnudos/2.0` 与 `ncurses/6.6` 制品仓均可拉取（`conan install --build=never` 通过）。
- 登记表原"等依赖 ncurses/6.5"**有误**：fontopia 真正依赖 GnuDOS，已改判并留痕。
- 无同软件历史 notes（`archives/f` 无 fontopia）。

## 上游测试账本（R51）
- 上游**无自动化测试**：无 `check`/`test` 目标、无 tests 目录与测试源。
- `N_static = 0`、`N_registered = 0`、`N_executed = 0`（如实申报）。
- 消费者测试（test_package）**1 程序 / 4 断言**：驱动已安装的 `fontopia` 二进制——
  ①`--version` 输出含版本号 `2.0`；②`--help` 退出码 0；③`--help` 含
  "Fontopia for GNU/Linux, Version" 横幅；④`--help` 含 Usage 段。

## 探索构建（真机实测，逐层剥开都有第一条真实错误）
1. `ncurses.h: No such file` —— gnudos 打包为 `package_type = "application"`，而 **Conan 2 不把
   application 包自身的依赖传递给消费者**；配方显式 `requires("ncurses/6.6")` 后解决。
2. `ld.lld: undefined symbol: fcloseall` —— musl 无 glibc 专有的 `fcloseall()`；补
   `patches/0001-musl-fcloseall-to-fflush.patch`（改用 `fflush(NULL)`，与同族 gnudos 2.0 既有补丁同法）。
3. `Error loading shared library libgnudos.so.2` —— gnudos 包里的 `libgnudos.so.2` 未通过
   OHOS ELF 签名校验，设备链接器拒载（对照：gnudos 自带的 `mino`/`prime` 是**静态**链的，
   `NEEDED` 里没有该 .so，所以能跑）。修法：`build()` 用 `make fontopia_LDADD="<gnudos>/lib/libgnudos.a
   <ncurses>/lib/libncursesw.a"` 覆写上游 `-lgnudos`，改为静态链接（ncurses/6.6 本身也只交付 `.a`），
   消费者二进制只依赖 libc，不受他人包签名状态影响。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `ncurses.h` 找不到 | application 包的依赖不向消费者传递（Conan 2） | 显式 `requires("ncurses/6.6")` |
| 2 | `undefined symbol: fcloseall` | musl 无该 glibc 函数 | 补丁改用 `fflush(NULL)` |
| 3 | 运行时 `libgnudos.so.2` 拒载 | 依赖包 .so 未过 OHOS ELF 签名校验 | `fontopia_LDADD` 覆写为静态归档 |
| 4 | HMDFS/CI worker 上 configure 失败 | E386 家族（CONFIG_SHELL 指向 hnp bash 时 getcwd 挂）+ E011（configure 内 umask 077） | 源码树内 `env CONFIG_SHELL=/bin/sh SHELL=/bin/sh ./configure`；`umask 077`→`022` |

## 源码修改

| 补丁 | 内容 | 原因 |
|------|------|------|
| `patches/0001-musl-fcloseall-to-fflush.patch` | `src/main.c`：删除 `extern int fcloseall(void)` 声明，`fcloseall()` → `fflush(NULL)` | musl 无 `fcloseall()`（glibc 专有），链接期 `undefined symbol` |

## 依赖版本
- `gnudos/2.0`（提供 `console/*.h` 与 `libgnudos.a`，静态链）
- `ncurses/6.6`（gnudos 的终端库，本身只交付静态 `.a`）

## 验证结果

```bash
export PATH=$HOME/.local/bin:$PATH TMPDIR=$HOME/tmp \
       CONAN_HOME=$HOME/tmp/ch/home-ds4-fontopia SSL_CERT_FILE=$HOME/usr/local/ssl/cert.pem
cd ~/qzy/DS-4-fontopia-2.0
python3 scripts/ohc-run.py conan-verify fontopia 2.0
```
（结果见 `reports/conan-verify-report.md`；消费者测试 4/4 断言通过）

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/fontopia` | 控制台字体编辑器（aarch64/OHOS ELF，静态链 gnudos/ncurses，仅依赖 libc） |
| `info/fontopia.info`、`man/man1/fontopia.1` | 上游 info/man 文档 |

## 注意事项
- 本包链接的是**静态** `libgnudos.a` + `libncursesw.a`：这是绕开依赖包未签名 `.so` 的受控选择，
  不是随手改链接方式；若后续 gnudos 包补齐 `.so` 签名，可再评估改回动态链接。
---

**编译结束**: 2026-09-21 11:09
**最终状态**: built
