# bsd-games 3.3 适配笔记

## 软件信息
- **名称**: bsd-games 3.3
- **上游**: https://bsd-games.sourceforge.io/（sourceforge 官方项目）
- **描述**: 经典 BSD 文本终端游戏合集（18 个游戏）
- **构建系统**: 手写简化 autotools（configure + make，非标准 autoconf）
- **许可证**: BSD-3-Clause

## 依赖
- **ncurses/6.6**（conan 制品仓 ohpcd 已发布，W0 检查通过）

## 编译适配过程
1. **configure**: 手写 configure 脚本（199 行），通过 pkg-config 探测 ncurses
   - 支持的选项：`--prefix/--bindir/--datadir/--mandir/--wordlist/--localstatedir/--builddir/--with-debug/--with-native`
   - 不支持 `--enable-static/--disable-shared`（会报 unrecognized option）
2. **关键问题 1 — curses.h 找不到**：
   - 现象：`fatal error: 'curses.h' file not found`
   - 根因：conan ncurses 包只有 `ncursesw.pc`（无 `ncurses.pc`），configure 的 `pkg-config --cflags ncurses` 探测失败 → 回退默认 `-lncurses`（不含 -I 头文件路径）
   - 修复：在 PKG_CONFIG_PATH 中提供 `ncurses.pc → ncursesw.pc` 别名（conanfile.py `_pkg_config_env()` 中在 build_folder 下复制一份 ncurses.pc）
   - 注意：探索阶段直接在 conan 缓存包内创建了软链，正式配方用 build_folder 副本方案（不污染 conan 缓存）
3. **关键问题 2 — install 报 bad group 'users'**：
   - 现象：`install: bad group 'users'`
   - 根因：Config.mk.in 中 `INSTALL_SCORE := ${INSTALL} -m 664 -g users /dev/null`，OHOS 无 users 组
   - 修复：去掉 `-g users`（探索阶段直接改源文件，待 refresh-patch 固化）
4. **make 注意**：`-j2` 报 `jobserver mkfifo: Operation not permitted`（HMDFS 限制），必须 `-j1`

## 测试情况（R51）
- **上游测试**: 无。源码包 122 个文件无 tests/ 目录、顶层 Makefile 无 test/check 目标；Alpine aports APKBUILD 官方标注 `options="!check" # no tests`（与上游一致）
- **自研测试**（test_package，21 断言）:
  - 18 个游戏二进制存在且可执行
  - caesar 无参数走频率分析（find_best_rotation 选中偏移 23）：`echo "Hello World" | caesar` == `Ebiil Tloia`
  - caesar 显式偏移 13：`echo "Hello" | caesar 13` == `Uryyb`
  - wump -h 输出 Usage 用法文本

## 产物
- 18 个游戏可执行文件（adventure/arithmetic/atc/battlestar/caesar/cribbage/dab/drop4/gofish/gomoku/hangman/klondike/robots/sail/snake/spirhunt/worm/wump）
- man 手册（man6 下 18 个 .6.gz）
- score 文件（var/lib/bsdgames/ 下按游戏生成）
- 纯应用包（无库文件），package_type = application，需要 commands.json（R38）
---

**编译结束**: 2026-09-07 15:54
**最终状态**: built
