# pspg 5.8.16 — HarmonyOS PC 适配说明

## 概况

`pspg` 是 Pavel Stehule 开发的面向表格数据的 Unix pager：为 psql/MySQL/
CSV/TSV 输出设计的表格浏览器（冻结表头/列、排序、搜索、导出）。

- 上游：https://github.com/okbob/pspg （官方 tag tarball，自带预生成 configure）
- 形态：手写根 Makefile + configure 生成 config.make（非 automake），in-source 构建
- 产物：`bin/pspg` 单一可执行文件
- 依赖：ncurses/6.6（含 panelw，菜单组件）、readline/8.3（可选上游依赖，
  保留完整搜索/历史功能）；PostgreSQL 为可选（未命中仅 NOTICE，不需 libpq）
- 许可证：BSD-2-Clause

## 适配要点

| # | 问题 | 处理 |
|---|------|------|
| 1 | ax_with_curses 在 pkg-config 命中 ncursesw 后直接定义 HAVE_NCURSESW_CURSES_H，而 ncurses/6.6 包头文件平铺 | compat-include/ncursesw/ 镜像层 + 前置 -I（gtypist/2.10.1 已验证方案） |
| 2 | tarball 无 config.guess（configure.ac 无 AC_CANONICAL） | 无需 --build 三元组，configure 直接运行 |
| 3 | 手写根 Makefile 相对路径编译 src/*.c | in-source 构建（`folders.build="."`） |
| 4 | CONFIG_SHELL 缺陷（§12.38①）；HMHDFS umask 077；jobserver EPERM | `env -u CONFIG_SHELL SHELL=/bin/sh` + 绝对路径；configure 生成脚本 umask 077→022 替换；`make -j1` |
| 5 | readline 检测为纯 -lreadline 链接探测 | AutotoolsDeps 注入 LDFLAGS，readline/8.3 直接命中 |
| 6 | CLI 工具门禁 | 软件级 `commands.json`（R38） |

## 测试

### 上游

无可自动化测试套件（Makefile 无 test 目标；tests/test.sh 是 100 轮循环的
psql 输出流生成器，供人工管道观察），原因完整记录在
test_package/MANIFEST.yml。

### 消费者（test_package/test_pspg.sh，6 项断言）

-V 版本 / --about / --help / 未知选项报错 / --csv 非 tty 渲染
fixtures/sample.csv / --tsv 渲染 fixtures/sample.tsv。非 tty stdout 下
pspg 走非交互渲染路径（pspg.c:2997）真实打印表格数据后退出，不初始化
ncurses，离线确定性可验证（R34）。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 5.8.16 | prepared | 首次适配，待真机验证（Windows 阶段 2026-09-26 完成） |
