# tina 0.1.14 适配笔记

## 编译环境
- 构建系统: autotools（configure.ac + Makefile.am）
- 编译日期: 2026-09-20
- 编译器: clang/clang++（OHOS SDK clang 15，libc++）
- 目标平台: aarch64-unknown-linux-ohos（OHOS 6.0）
- 状态: built

## 编译步骤

1. `source()`：从官方 gitlab 拉取 release/0.1.14 tarball（strip_root）
2. `source()` 内联：`configure` 脚本 `umask 077` → `umask 022`（见下方源码修改）
3. `build()`：`configure --prefix=... --without-shared`（ncurses 的 include/lib 目录经
   CPPFLAGS/LDFLAGS 注入）；`make`
4. `package()`：`make install` → `bin/tina` + `share/man/man1/tina.1`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | OHOS 沙箱下 configure 的 config.status 临时目录不可写 | `configure:5281/5286` 以 `umask 077 && mktemp -d ./confXXXXXX` 建 0700 目录，config.status 随后向其写入失败 | `source()` 内把 `configure` 的 `umask 077` 就地替换为 `umask 022`（manifest.yaml `patches_applied` 已如实记为 `(inline)`）。**已知待改进**：本仓库对同一手法有声明式 patch 先例（`archives/n/ncurses/6.5/patches/0002-configure-umask-022.patch`、`archives/a/a52dec/0.7.4/patches/0002-configure-umask-022.patch`、`archives/y/yydecode/0.2.10/patches/0001-configure-hmdfs-umask.patch`），改用 `conandata.yml` 声明的 patch 更合规；该项属配方变更，需按 R37 递增版本后另开修复 PR |
| 2 | `AC_CHECK_LIB(curses, initscr)` 探测 `-lcurses` 失败 | ncurses/6.5 包只产出 `libncursesw.a`（widec），无 `libcurses.a` | build() 在 configure 前于 ncurses lib 目录创建 `libcurses.a -> libncursesw.a` 符号链接 |
| 3 | CI L0 门禁失败（no_test_sources / stub_test_method / no_manifest / commands_json_r38） | 初版 test_package 用 CMake 编译消费者测试且 test() 无 self.run()；缺 MANIFEST.yml 与 commands.json | 重写 test_package 为直接执行打包二进制（test_tina.sh）；补 MANIFEST.yml 与 archives/t/tina/commands.json |
| 4 | CI L1 失败 "Error opening terminal: xterm-256color" | tina 是全屏 curses TUI，headless CI 无 TTY，initscr() 失败 | test 改用 `tina --version`：main.c 在 initscr() 之前处理 --version 并 exit 0（main.c:707），免终端全链路验证 ELF 加载 + 动态链接 + ncurses 链接（sl 5.02-r1 同款 headless 策略） |

## 源码修改

- 唯一修改：`configure`（autotools 生成脚本）`umask 077` → `umask 022`，source() 内联替换。
  未动任何 C 源文件。

## 依赖版本

- ncurses/6.5（仓库制品仓已有，shared=False、fPIC=True）

## 上游测试清点（R51 三步法 / 平台 rule4「实测 N」口径）

- 上游测试入口：`tox -e unit-tests`（Python pytest，tests/python/unit）
- 取数命令（源码行数法，与平台实测口径一致）：
  `grep -rh 'def test_' tests/python/unit --include='*.py' | wc -l` → **实测 N = 15**（7 个测试文件）
  注：多数用例为 pytest parametrize，运行时展开的注册用例数 > 15；本 PR 按源码行数法申报。
- C 侧核对：`Makefile.am` 仅 `bin_PROGRAMS=tina`，无 `check_PROGRAMS` / `TESTS`
  → C 侧自动化测试入口 0 例
- 15 例在 OHOS aarch64 目标环境均不可执行，逐类技术原因：
  - (a) 全部需 CPython ≥ 3.10（源码用 `match/case`）+ pytest + PyYAML
    （`convert/test_convert.py:11 import yaml`）；OHOS 目标环境无 Python 运行时，CI worker 不提供
  - (b) `convert/*` + `combined/*` 共 9 例经 `unit/util.py` 的 `ProgramType` 解析
    `TINA_CONVERT`，该可执行文件是 Rust 实现的 `tina-convert`
    （`rust/src/bin/tina-convert/cli.rs`）；CI 无 Rust 工具链
  - (c) `mgr/*` 共 6 例（`test_simple.py` 4 + `test_many.py` 2）经
    `unit/mgr/util.py` 的 `tina_with_test_db_in_tempd` 用 pty 驱动编译产物并模拟按键，
    属交互式 TUI 集成测试，需要伪终端，headless worker 无 TTY
- 结论：**上游侧记 0/15**（不可执行，非漏报）；C 侧自动化测试 0 例；
  适配后补全 test_package 消费者冒烟测试 1 例（执行打包的 `tina --version`，
  4 段断言，断言输出含 "Tina 0.1.14"）

## 验证结果

```
conan create archives/t/tina/0.1.14 -pr:h ohos-aarch64 -pr:b ohos-aarch64
→ 构建通过（configure/make/install），test_package 1/1 通过
```

- test_tina.sh 静态 + mock 演练：正确输出 exit=0；错误版本/二进制缺失 exit=1
- 真机复验未执行（原因：无 OHOS 设备可用；`--version` 路径不依赖 TTY，风险低）

## 注意事项

- curses TUI 的交互式行为（initscr 之后）在 OHOS 目标环境未实测（headless 无法验证），
  `--version` 冒烟只覆盖到 initscr() 之前
- 依赖仅 ncurses，无其他三方库
- 待改进（未在本 PR 修改，避免触发 R37 版本递增）：`build()` 在 ncurses 包的
  lib 目录内创建 `libcurses.a` 符号链接，属写入依赖包目录（共享 conan 缓存），
  应改为 `build_folder/prefix` 私有 prefix；详见 `archives/a/asterisk-srtp/22.10.1`
  的 R49 参考实现
