# ucblogo 6.2.5 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-30
- 编译器: clang/clang++ (OHOS clang 15)
- 状态: prepared / unverified

## 上游身份

- 官方仓库: https://github.com/jrincayc/ucblogo-code
- tag: `version_6.2.5`
- tag object: `53eda46a85e51d6a3c177c9f3989e37fc44d86c8`
- peeled commit: `a0215433f07384e4c42fe247525867f11e6f32f7`
- 源码包: `https://github.com/jrincayc/ucblogo-code/releases/download/version_6.2.5/ucblogo-6.2.5.tar.gz`
- SHA256: `8f4033a79c95efd0d4d2fb257b1f45dd7ba33cf7a2c8d942c29b5467ce31a4fa`
- 许可证: `GPL-3.0-or-later`

官方 6.2.5 release 资产包含完整 `configure`、`Makefile.in`、`config.h.in` 和辅助脚本；配方直接使用该 release 资产，不依赖设备侧缺失的 automake/libtool，也不随包维护生成文件副本。

## configure 参数

```text
--enable-objects
--disable-wx
--disable-x11
--disable-docs
LIBS=-lncursesw
```

`--enable-objects` 保持 OOP 解释器能力并启用上游 OOP 测试套件。只关闭 wxWidgets、X11 和文档，不关闭 Logo 核心解释器、文件读写或脚本执行。

## 终端依赖结论

上游没有内置 termcap 实现。`term.c` 直接调用 `tgetent`、`tgetstr`、`tgetnum`、`tputs` 和 `tgoto`；`configure.ac` 通过 `AC_SEARCH_LIBS(tgetstr, [termcap termlib curses ncurses])` 查找库。

OHOS 构建使用制品仓已发布的 `ncurses/6.4`（`shared=False`）静态包。`AutotoolsDeps` 注入头文件和库目录，configure 使用 `LIBS=-lncursesw`，不硬编码设备路径，也不选中系统共享 ncurses。此项与仓库中其他终端配方的 Conan 依赖方式一致。

## 源码修改

配方应用 `patches/0001-ohos-termios.patch` 并以 `HAVE_TERMIOS_H=1` 注入编译定义。源码逻辑修改只有一处：

1. `term.c` 在 `HAVE_TERMIOS_H` 下优先使用 `termios.h`/`sys/ioctl.h`、`struct termios`、`TCGETS` 和 `TCSETS`。

原因: OpenHarmony musl 源码树没有 `termio.h` 或 `sgtty.h`，只有 `termios.h`。未打补丁时，关闭 wx 后 `term.c` 会回落到旧式 `TIOCGETP`/`TIOCSETP` 分支并因缺少 `struct termio` 而无法编译。

## 上游真实测试

官方 CI 配置位于 tag 的 `.github/workflows/ci.yaml`，执行命令为：

```bash
cd tests
LOGOLIB=$GITHUB_WORKSPACE/logolib \
  xvfb-run -e /dev/stdout --auto-servernum \
  $GITHUB_WORKSPACE/ucblogo UnitTests.lg - \
  -f $GITHUB_WORKSPACE/logo-unit-test-results.txt -x
```

CI 使用以下两条 awk 判定失败：

```bash
awk '/\.\.\./ && ! /Ok$/{print "::error::"$0}' logo-unit-test-results.txt
awk '/\.\.\./ && ! /Ok$/{exit 1}' logo-unit-test-results.txt
```

OHOS 配方关闭 wx/X11，所以不调用 `xvfb-run`，其余参数保持同一测试框架与输出格式。`build()` 真实执行该测试，并验证结果必须恰好包含 10 个 suite 和 94 个命名 case。逐项数量见 `test_package/MANIFEST.yml`。

上游 6.2.5 release tarball 的 `UnitTests.lg` 会加载 `UnitTests-Files.lg`、`UnitTests-Macros.lg` 和 `UnitTests-Control.lg`，但该发布包遗漏了这三个文件。配方保留 release 包中已生成的 Autotools 文件用于构建，另从同一 `version_6.2.5` 官方 tag 归档按固定 SHA256 恢复这三个原始测试文件，并逐个校验文件哈希。测试内容与上游 tag 完全一致，没有删减或改写。

上游测试文件未修改。消费者测试另行执行，不计入 94 个上游 case。

## 风险

- 配方文件清单中的状态仍为 prepared/unverified；OpenDesk 隔离验证结果由 PR 正文记录。
- 终端依赖使用仓库发布的 `ncurses/6.4`（`shared=False`），不依赖设备硬编码安装前缀。
- release 资产中的 Autotools 输出由上游发布；升级版本时需要重新核对 release 资产和 SHA256。
- OHOS 交互式 TTY 行为未验证；上游解释器和测试模式不依赖常驻 GUI。

## 消费者验证

`test_package/test.sh` 对安装产物执行 7 项独立检查，与上游 94 个 case 分开计数：

执行 Logo 程序前，脚本把已安装的 `share/ucblogo/logolib`、`share/ucblogo/helpfiles`、`share/ucblogo/csls` 分别导出为 `LOGOLIB`、`LOGOHELP`、`CSLS`。这是上游解释器定位 `startup.lg` 和运行时资源的正式环境变量接口，不依赖构建目录。

1. `bin/ucblogo` 存在且可执行。
2. `share/ucblogo/logolib` 目录存在。
3. `share/ucblogo/helpfiles` 目录存在。
4. `share/ucblogo/csls` 目录存在。
5. `share/ucblogo/logolib/Messages` 可读且非空。
6. 安装后的解释器真实执行 Logo 算术程序并输出 `42`。
7. 输出包含 `UCLBLOGO_CONSUMER_OK`，且不包含 `UCLBLOGO_CONSUMER_FAIL`。
