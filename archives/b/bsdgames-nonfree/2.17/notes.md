# bsdgames-nonfree 2.17 适配笔记

## 编译环境
- 构建系统: custom（交互式 configure 脚本生成 GNUmakefile）
- 编译日期: 2026-09-06
- 编译器: clang 15.0.4（target: aarch64-unknown-linux-ohos）
- 状态: built

## 编译步骤

1. configure 非交互模式（该包 configure 为交互式脚本，通过 `bsd_games_cfg_*` 环境变量预设默认值）：
   ```bash
   export bsd_games_cfg_non_interactive=y bsd_games_cfg_cc=clang \
     bsd_games_cfg_optimize_flags="-O2" \
     bsd_games_cfg_ncurses_lib="-L$NCURSES_DIR/lib -lncursesw" \
     bsd_games_cfg_ncurses_includes="-I$NCURSES_DIR/include" \
     bsd_games_cfg_do_chown=n bsd_games_cfg_gzip_manpages=n \
     bsd_games_cfg_use_libcrypto=n \
     bsd_games_cfg_install_prefix=<staging前缀>
   ./configure
   ```
2. `make -j2` 编译成功
3. `make install` 安装到 staging（该包无 DESTDIR 机制，通过 INSTALL_PREFIX 前缀实现 staging）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `rogue/machdep.c` 编译报 `O_RDONLY` 未定义 | 源文件缺 `<fcntl.h>`（BSD 代码依赖 `<sys/file.h>` 传递包含，OHOS libc 不传递） | 在 machdep.c 头文件区添加 `#include <fcntl.h>` |
| 2 | `make install` 报 `/usr/games: Permission denied` | 该包安装规则为 `$(INSTALL_PREFIX)$(GAMESDIR)`，configure 默认 install_prefix 为空导致安装到系统绝对路径 | configure 时设置 `bsd_games_cfg_install_prefix=<staging前缀>` |

## 源码修改

- `rogue/machdep.c`: 添加 `#include <fcntl.h>`（由 refresh-patch --auto 生成补丁）

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| ncurses | 6.4（conan 制品仓 ohpcd，静态库） | curses 终端界面（-lncursesw） |

- 说明：本包（bsd-games-non-free）仅包含 rogue 一个游戏；configure 中 factor 的 openssl/libcrypto 为可选依赖，已关闭（bsd_games_cfg_use_libcrypto=n）。

## 上游测试清点（R51 三步法）

- 上游 `tests/` 目录共 150 个文件，含 10 个 `.test` 脚本：battlestar/bcd/caesar/factor/morse/number/pig/pom/ppt/primes
- **全部 10 个测试脚本针对的游戏二进制（battlestar/bcd/caesar/factor 等）均不在本包构建范围内**——本包（bsdgames-nonfree 2.17）仅构建 rogue 一个游戏（`find . -name Makefrag` 仅有 `lib/` 与 `rogue/`）
- 实测运行：10 个测试脚本全部因 `tests/common` 中 `testexec` 检查目标二进制不存在而 `exit 0` 跳过（rc=0 但无任何断言执行）
- 结论：上游测试对本包零可运行，须自研 test_package 断言补齐（rogue 功能验证）

## 验证结果

```bash
# rogue 二进制可运行（交互式游戏，等待输入名字）
echo "q" | timeout 5 <prefix>/usr/games/rogue   # 输出 "Hey!  Who are you?" 后正常退出
# 动态依赖仅 libc.so（ncursesw 静态链接）
llvm-readelf -d rogue | grep NEEDED   # libc.so
```

## 注意事项

- 该包 configure 是自定义交互式脚本，非标准 autotools，不支持 `--prefix` 参数；必须用 `bsd_games_cfg_*` 环境变量预设
- 安装布局：二进制在 `usr/games/rogue`（非 bin/），manpage 在 `usr/share/man/man6`，文档在 `usr/share/doc/bsd-games`，scorefile 在 `var/games`
- rogue 为交互式 roguelike 游戏，测试需通过 stdin 模拟输入
---

**编译结束**: 2026-09-07 01:28
**最终状态**: built
