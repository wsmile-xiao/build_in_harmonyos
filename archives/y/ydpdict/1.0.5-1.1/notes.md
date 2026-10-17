# ydpdict 1.0.5-1.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-29
- 编译器: clang（OHOS SDK，aarch64-linux-ohos）
- 状态: built

## 编译步骤

configure/make 由 Conan autotools 生成器驱动，关键点：

- `./configure --prefix=... --without-libao`（libao 为可选音频后端，未适配时 configure 静默降级）
- configure 要求 **Unicode ncurses**：`AC_CHECK_HEADER([ncursesw/ncurses.h])` + `AC_CHECK_LIB([ncursesw],[initscr])`，
  因此依赖使用 `ncurses/6.6`（提供静态 `libncursesw.a`），不使用系统 curses
- 依赖路径必须在 `build()` 中以命令前缀强制注入 `-I<dep>/include -L<dep>/lib`（原因见"遇到的问题" #2）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 `Invalid configuration 'aarch64-unknown-linux-ohos': OS 'ohos' not recognized`（E007） | 上游 `config.guess`/`config.sub` 不认识 HarmonyOS 主机三元组 | 新增 `patches/0001-config.guess.patch`（HarmonyOS 主机分支，归一化为 `*-unknown-linux-ohos`）与 `patches/0002-config.sub.patch`（OS 白名单增加 `ohos*`）；干净副本 dry-run 双通过，未使用平台宏 |
| 2 | `AC_CHECK_HEADER(ncursesw/ncurses.h)` 找不到头，configure 报 no | profile `[buildenv]` 的 `CPPFLAGS='-I$HOME/usr/local/include -DNDEBUG'`、`LDFLAGS='-L$HOME/usr/local/lib'` 覆盖了 `generate()` 注入的依赖路径 | 在 `build()` 里把依赖 `-I/-L` 直接拼进编译命令前缀（前缀赋值写法在 POSIX shell 中先展开同行参数，取不到新值） |
| 3 | TUI 用例"渲染成功但进程不结束"（rc=3） | 上游 `main()` 无 `--version/--help` 等非交互分支，进入后无条件 `initscr()` 等待按键，pty 下退出键行为不定 | 按 R43 改为确定性断言：渲染成功 + 退出键或 `SIGTERM` 兜底终止（rc=0） |
| 4 | TUI 初始化报 `cannot initialize terminal type` | 平台系统 terminfo 仅含 `xterm-256color`/`screen-256color`，且 terminfo 在依赖包中分布于 `share/` 与 `lib/` 两处 | `pty_drive.py` 自动挑选真实存在的 TERM，按 `TERMINFO_DIRS` 多目录发现（依赖包优先、系统兜底） |
| 5 | 消费者编译 `fatal error: 'ydpdict/ydpdict.h' file not found` | 同 #2（`$CPPFLAGS` 前缀赋值时序问题） | test_package `build()` 中把 `-I/-L` 直接拼进命令行 |

## 源码修改

- `patches/0001-config.guess.patch`：新增 HarmonyOS 主机分支（aarch64→aarch64、armv7*/armv8*→arm、x86_64→x86_64、i?86→i686，输出 `*-unknown-linux-ohos`）
- `patches/0002-config.sub.patch`：OS 白名单增加 `ohos*`，CPU 别名增加 aarch64
- 上游业务源码零修改（`src/*.c` 未改动）

## 依赖版本

| 依赖 | 版本 | 说明 |
|---|---|---|
| ncurses | 6.6 | 需 Unicode 版（静态 `libncursesw.a`） |
| libydpdict | 1.0.4 | 词典引擎（制品仓已发布） |
| libao | — | 可选音频后端，未适配，以 `--without-libao` 关闭 |

## 验证结果

```bash
conan create archives/y/ydpdict/1.0.5-1.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
# → rc=0；平台断言 7/7 通过，消费者 C 用例 16/16 断言通过（failures=0）
```

## 交付物

| 文件 | 说明 |
|------|------|
| `conanfile.py` | autotools 配方（ncurses / libydpdict 依赖，`--without-libao`） |
| `conandata.yml` | 源码 URL + sha256 + 2 个补丁声明（list 形式） |
| `test_package/` | 平台 + TUI + 消费者用例（7 组平台断言 + 16 条消费者断言） |

## 注意事项

- 本机直连 GitHub 不可达，源码经镜像获取并以 sha256 与官方源比对一致。
- 上游无测试用例（清点证据见 `reports/test-report.md` §1）。
- R38：产物含 `bin/ydpdict` 可执行文件，软件级 `commands.json`（`type=tool`）已提供。

---
**编译结束**: 2026-09-29 15:31
**最终状态**: built
