# libnewt 0.52.25 适配笔记

## 编译环境

- 构建系统：autotools 风格（configure 脚本 + 手写 Makefile.in，非 automake）
- 适配日期：2026-09-17
- 编译器：clang（HarmonyOS aarch64 真机，与官方 CI 同源）
- 依赖：slang/2.3.3（S-Lang）、popt/1.16（仓内均已有归档）
- 状态：待 HMBS 真机预检

## 编译步骤

```bash
./configure --without-python --without-tcl --disable-nls
make -j1 GNU_LD=ld
make install
```

说明：

- `--without-python`：OHOS 无 python 开发头，跳过 `_snack.so` 构建。
- `--without-tcl`：OHOS 无 `tclConfig.sh`，跳过 `whiptcl.so`。
- `--disable-nls`：OHOS 无 libintl；不加则 configure 因找不到 gettext 而直接失败。
- `make GNU_LD=ld`：configure 按 `ld -v` 是否含 "GNU ld" 判断，OHOS 下为空，
  必须在 make 命令行给出非空 `GNU_LD` 才能走 `-soname/--version-script` 分支，
  否则 `libnewt.so` 缺少 `DT_SONAME`（L5a 门禁要求）。
- 构建为源码树内构建：`Makefile.in` 无 VPATH 支持，配方把源码同步到 build
  目录后再 configure/make。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | OHOS 无 standalone `install(1)`，`make install` 失败 | 真机缺 `install` 命令 | 配方在 build 目录生成 `.hmbs-bin/install` shim（支持 `-c/-m/-d` 与文件复制），`PATH` 前置 |
| 2 | HNP bash 在 HMFS/HMDFS 下 `getcwd()` 失败导致 configure 中止 | HMBS buildenv 的 `SHELL/CONFIG_SHELL` 指向 HNP bash | `generate()` 用 `Environment` 定义为 `/bin/sh`，并在 `conanbuild.sh` 末尾追加覆盖（most 5.2.0 已验证模式） |
| 3 | autoconf 样板 `umask 077` 在 HMDFS 下导致 config.status 写失败 | HMDFS 权限语义（E011） | 构建前把 build 目录内 `configure` 的 `umask 077` 替换为 `umask 022` |
| 4 | `libnewt.so` 无 `DT_SONAME` | configure 的 GNU ld 探测在 OHOS 下为空 | `make` 时传 `GNU_LD=ld` 强制走 soname 分支（lld 支持 `--version-script` 与 `-soname`） |
| 5 | configure 报 `C compiler cannot create executables`（真机两轮复现，TMPDIR 导出后仍失败） | OHOS 下裸 `clang` 缺 `--target` 找不到 CRT/链接失败（E001；同仓 slang/2.3.3 已验证） | `generate()` 在 OHOS 时向 extra_cflags/cxxflags/ldflags 追加 `--target=aarch64-unknown-linux-ohos` |
| 6 | 真机 `/tmp` 只读致临时文件失败（HMBS readonly_tmp 诊断） | `/tmp` 为 erofs 只读，configure/clang/mktemp 默认落 `/tmp` | `_writable_tmpdir()` 复用 HMBS 注入的可写 TMPDIR（回退 build_folder/tmp），generate/build/conanbuild.sh/make 全链路导出（c-client 已验证模式） |
| 7 | 前两轮修法同步后 `C compiler cannot create executables` 第三次复现 | 疑点转向：popt 朴素配方有可用二进制，同机裸 clang 可链接；同仓 cassbeam 记录 `/data/service/hnp/bin/clang` 在 conan 构建域可出现 "inaccessible or not found" | `build()` 实测 conf CC 是否可执行（`--version` 探针），可用则原文照用、不可用则回退 PATH 上实测可用的编译器；CC 恒带 `--target`（configure 改写 CFLAGS 也不丢）；`_fix_umask` 改字节级替换；configure 失败时打印 config.log 尾部留真凭 |
| 8 | `package()` 的 `make install` 在 `po/` 子目录报 `/bin/sh: /usr/bin/install: inaccessible or not found`（数十次）致 `Error 127/2` | 双重原因：① 顶层 Makefile 用裸 `install`（PATH 垫片可覆盖）；② 静态 `po/Makefile` 硬编码绝对路径 `/usr/bin/install -c`（configure 不生成该文件，PATH 无法覆盖；etsh/5.4.0 证实 OHOS 真机 install 在 `/system/bin/install`）；且 `--disable-nls` 下仍递归进 `po/` | `_resolve_install()` 优先用 `/system/bin/install`（toybox，存在可执行时），否则用增强版 `.hmbs-bin/install` 垫片（支持多源复制、`-D/-t/-m/-o/-g`）；`package()` 显式传 `INSTALL/INSTALL_PROGRAM/INSTALL_DATA/INSTALL_SCRIPT=<bin> -c` + `MKINSTALLDIRS=mkdir -p` 覆盖绝对路径，`INSTALL_NLS=` 置空杜绝 NLS 关闭时仍进 `po/`；`_fix_conanbuild_shell()` 持久化 `PATH` 使裸 `install` 在 conanbuild 环境下仍命中 |
| 9 | 上轮修复后 `package()` 仍 `Error 2`，日志出现 make 用法帮助（`-W FILE... This program built for...`） | 上轮 `INSTALL=<bin> -c` / `MKINSTALLDIRS=mkdir -p` 等值含空格，make 按空格切分为杂散 `-c/-p` 选项直接打印用法退出；另真机能力 `chmod:0`（chmod 不支持）使垫片 `chmod` 可能失败，且 `package()` 未显式传 `TMPDIR`（readonly_tmp 仍被点名） | 传值全部改为单 token（去 `-c` 后缀，`MKINSTALLDIRS` 改用无空格 `.hmbs-bin/mkinstalldirs` 包装脚本）；垫片 `chmod` 改 best-effort（`|| true`）；`_resolve_install()` 优先复用 hmbs 注入的 `HMBS_INSTALL`（平台能力 `install_shim:true`），`generate()` 透传该变量；`package()` 的 install 调用显式传 `SHELL/TMPDIR/TMP/TEMP` |
| 10 | 主包 `package()` 已过（日志出现 showchars 链接行并进入 test_package），`test_package` 的 `cmake.configure()` 报 `CMAKE_C_COMPILER: /data/service/hnp/bin/clang` 无法编译简单测试程序 | 与主包同源 E001：裸 clang 缺 `--target` 链接失败；且 conf 编译器二进制在此域可能不可运行（cassbeam 先例）；test_package 默认 CMakeToolchain 未做主包同款处理 | test_package 的 `CMakeToolchain` 改在 `generate()` 内定制：探针实测可用 CC（列表式无 shell 直调）写入 `CMAKE_C_COMPILER`，OHOS 时 `extra_cflags/cxxflags/ldflags` 追加 `--target`；另经 buildenv 导出可写 `TMPDIR/TMP/TEMP` 与 `SHELL`（readonly_tmp 最小适配） |

## 源码修改

无补丁。全部平台处理均在 `conanfile.py` 内完成（configure 参数、Makefile 变量、
install shim、SHELL 覆盖），`patches/` 目录无需创建。

## 依赖版本

- slang/2.3.3（S-Lang，仓内归档，状态 built）
- popt/1.16（仓内归档，状态 built）

## 上游测试审计

上游 newt 0.52.25 无任何自动化测试：

- `Makefile.in` 无 `check` 目标；`configure.ac` 无测试框架绑定。
- `test.c/testgrid.c/testtree.c/showchars.c/showkey.c` 为交互式 TTY 演示程序，
  需终端输入，不是自动化断言。
- BLFS 明确记载 "This package does not come with a test suite."。

因此 `test_package/MANIFEST.yml` 声明 `upstream_tests_exist: false` 并附审计说明，
`test()` 输出 `status:"no_tests"` 标记（most 5.2.0 同款模式）。

| 11 | 静态包 test_package Error 127：静态重链接 whiptail 报 undefined useFullButtons/setButtonText/messageBox/checkList/inputBox/listBox/min/max，随后动态 whiptail 报 symbol not found newt* | 上游链接规则为 whiptail: \$(NDIALOGOBJS) \$(LIBNEWTSH)，NDIALOGOBJS=whiptail.o dialogboxes.o；上一轮配方只链接 whiptail.o+libnewt.a，漏掉 dialogboxes.o，且先删 .so 再重链接导致失败后无回退 | 重链接输入改为 whiptail.o+dialogboxes.o（缺 .o 时由对应 .c 补齐），与上游一致；package() 改为先重链接、仅成功时才删 .so，失败保留动态可用件并返回 False |\n\n## 验证结果

待 HMBS 真机预检回填（conan create 全链路：configure → make → install →
test_package 2 项）。本轮不提交、不推送。

test_package 设计（2 项，全部无需终端）：

1. `test_newt`：链接 `libnewt`，读取导出的 `newtDefaultColorPalette` 数据符号并
   校验公共宏/标志位（`newtInit` 需终端，刻意不用）。
2. `whiptail --version`：随包安装的二进制；该路径在 `newtInit` 之前退出，
   断言输出含 `whiptail (newt): 0.52.25` 且退出码为 0。

## 交付物

- `lib/libnewt.a`、`lib/libnewt.so.0.52.25`（+ `libnewt.so.0.52` / `libnewt.so` 符号链接）
- `include/newt.h`、`lib/pkgconfig/libnewt.pc`
- `bin/whiptail` 及其 man 页、po 翻译文件

## 注意事项

- `newtInit/newtFinished` 及全部窗口/组件 API 需要真实终端，CI 与 test_package
  均无法调用；消费者测试只覆盖无终端可验证面，已在 PR 正文如实说明。
- GPM 鼠标支持（`--with-gpm-support`）为 Linux 特有，未启用。
