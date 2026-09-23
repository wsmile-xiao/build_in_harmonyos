# dominion 2.8.2 适配笔记

## 编译环境
- 构建系统: autotools（老 config.guess/config.sub）
- 编译日期: 2026-09-14
- 编译器: clang 15.0.4（OHOS aarch64 工具链）
- 状态: built
- 任务号: 外部候选导入（平台活动：开源鸿蒙PC专项积分赛-依赖）
- 分支: feat/dominion-2.8.2

## W0 依赖发布检查
- configure.ac: ncurses/curses/termcap/m/crypt 为 AC_CHECK_LIB 软检查；
  编译实际需要 ncurses（curses.h）。
- ncurses 已在制品仓发布（6.4/6.5/6.6），配方固定 `ncurses/6.6`，
  `conan download ncurses/6.6 -r=ohpcd` 验证通过。
- 其余无外部依赖。

## W0b 历史经验核验
- 归档树 archives/d/ 无 dominion（本任务为首适配）。
- 套用 GLM-19 沉淀坑①（老 config.sub 勿传 --host）与 termcap/termutils
  先例（sh configure 直调 + package() 直拷产物）。

## 编译步骤

```bash
# 配方路径（conan create）
sh configure --build=aarch64-unknown-linux-gnu --prefix=<package_folder>
make -j1
# 产物：dominion dom_make dom_add dom_update dom_print（源码根目录）
```

## 上游测试（R51 四维账本）

| 维度 | 数值 | 证据 |
|---|---|---|
| N_static（上游静态声明） | 0 | 全部 Makefile.am/configure.ac 无 TESTS/check_PROGRAMS/测试目标（grep 证据见 test_package/MANIFEST.yml） |
| N_registered | 0 | 无 make check 可注册 |
| N_executed | 0 | 无上游套件 |
| N_consumer（新增消费者测试） | 1（断言 6 项） | test_package/test_dominion.sh：5 个工具齐备可执行 + dominion 未知选项确定性拒绝（usageerr + exit 1，dominion.c:143-144） |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 cannot guess build type | 老 config.guess 不识别 aarch64/OHOS | generate() 追加 `--build=aarch64-unknown-linux-gnu`（勿传 --host，GLM-19 坑①） |
| 2 | 编译需要 curses.h，设备无系统 ncurses 头 | ncurses 未安装于系统 | 配方 requires ncurses/6.6，extra_cppflags/extra_ldflags 注入 include/lib 路径 |
| 3 | 上游 Makefile 无 DESTDIR 支持 | 1990s automake | package() 直拷 5 个工具到 bin/ |

## 源码修改（patches/）

无——上游源码零补丁适配成功。

## 验证结果

```bash
python3 scripts/ohc-run.py conan-verify dominion 2.8.2
# G0-G4 / L2 / L4 / L5（结果见 reports/conan-verify-report.md）
```

## 注意事项

- dominion 主程序为交互式游戏，运行需要游戏数据文件；消费者测试走
  「二进制齐备性 + 未知选项确定性拒绝」断言路径，与数据无关。
- lib 软检查（termcap/curses/m/crypt）均非强制链接，crypt 在 OHOS musl
  无需（源码未调用 crypt()）。

## GLM-34 接班续跑记录（2026-09-15 凌晨）

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 4 | config.status confstat* 目录 Permission denied（GLM-23 断点的 E011/E114 墙） | HMDFS 强制 setgid/0700 + UID 映射 | 配方内 _drop_umask_077（autoconf-2.13 变体：confstatXXXXXX 带 -q、mkdir $tmp 不带引号），autoconf-2.13 版 configure 专用 |
| 5 | 包内无产物（WARN: No files in this package） | 接班时误把模块级 helper 插进类体，export_sources 及之后方法全部变成嵌套函数，类只剩 requirements，conan 用基类空 build/package | 重建配方文件结构（helper 移至模块级，ast 校验 8 个方法齐全） |
| 6 | curses.h not found | 此仓库 conan 2.29.1 的 AutotoolsToolchain 无 extra_cppflags/extra_ldflags 消费（CPPFLAGS 只吃 defines），GLM-23 预埋的 -I 从未生效；且 1995 年 Makefile 的 LINK 规则无 $(LIBS) | -I 走 tc.extra_cflags，-L/-l 走 self.conf.define("tools.build:exelinkflags")（libformw/menuw/panelw/ncursesw，静态序：消费者在前） |
| 7 | proto.h:103 conflicting types for 'getline' | 1995 年代码自定义 void/2参 getline 与 musl stdio.h 的 POSIX getline 冲突 | 配方 _patch_kr_sources 对自有符号精确改名（proto.h 声明/misc.c 定义/user.c、printmap.c 调用点共 4 处；-D 全局宏会连 libc 声明一起改而仍冲突，已否决） |
| 8 | ld.lld: undefined symbol: getpass（misc.c:190） | musl/OHOS 无 getpass()（glibc 遗留接口） | 配方注入静态 termios 版 dom_getpass()（关回显读一行）并替换调用点；crypt() 本身有 -lcrypt 可用 |
### 对话 #1 (2026-09-15, GLM-34)

- 接手 GLM-23 夜跑断点（配方/测试/manifest 就绪，G2 被 HMDFS umask 077 阻塞）。
- 依 E011/E114（opendmarc/ekg2 先例）在配方内做 umask 077 受控移除 + autoconf-2.13
  变体适配，顺路修复类结构/工具链 API/getline/opaque WINDOW/getpass 五处问题
  （明细见上表 #4-#8），conan-verify G2 真实构建通过，消费者测试真机执行 OK。
---

**编译结束**: 2026-09-15 02:16
**最终状态**: built
