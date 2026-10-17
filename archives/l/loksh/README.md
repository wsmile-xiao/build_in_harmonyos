# loksh 7.9 — HarmonyOS PC 适配说明

## 概况

`loksh` 是 OpenBSD Korn shell (ksh) 的 Linux 移植版（dimkr/loksh），
目标是单一 `ksh` 可执行文件，作为轻量 POSIX/Korn shell 使用。

- 上游：https://github.com/dimkr/loksh （官方 GitHub release 资产）
- 形态：Meson（7.9 起从 autotools 迁移），捆绑 `subprojects/lolibc`
  （dimkr/lolibc，静态链入；官方 release tarball 已打包子模块）
- 产物：`bin/ksh` + man 页（ksh.1/sh.1）+ 文档
- 依赖：ncurses/6.6（制品仓已归档；行编辑功能；缺失时上游静默
  `-DSMALL`，配方已守门）
- 许可证：Public Domain（pdksh/OpenBSD ksh 沿袭；捆绑 lolibc 宽松许可）

## 适配要点

| # | 问题 | 处理 |
|---|------|------|
| 1 | 真机/CI PATH 无 meson，远端无可解析 meson 工具包 | vendored meson 1.11.2（conandata `meson_source`），`python3 -c` 进程内注入调用（zchunk/1.5.2、astroterm/1.0.9、libdvdnav/7.0.0 已验证方案） |
| 2 | GitHub tag tarball 不含 lolibc 子模块，meson setup 直接失败 | 钉官方 release 资产 URL（已实测含子模块 33 文件），sha256 核验 |
| 3 | ncurses 找不到时上游静默加 `-DSMALL` 砍掉命令行编辑 | 配方 build() 解析 build.ninja 检测 `-DSMALL` 即抛错；PkgConfigDeps 生成 ncursesw.pc 供 `dependency('ncursesw')` 解析 |
| 4 | 并行构建 HMDFS jobserver fifo EPERM（E074） | `ninja -j1` |
| 5 | 上游无测试套件（meson.build 无 test()） | 按赛事规则说明原因，test_package 自补 12 项消费者断言 |
| 6 | CLI 工具门禁 | 软件级 `commands.json`（R38） |

## 测试

### 上游

无测试套件（原因见上表 #5，test_package/MANIFEST.yml 有完整说明）。

### 消费者（test_package/test_loksh.sh，12 项断言）

基本执行 / 变量与算术展开 / for+printf / 管道 / 退出码传递 / 脚本
文件执行 / 位置参数 / test 内建 / 子 shell / while read here-doc /
函数定义与调用 / KSH_VERSION，全部离线、真实执行包内 ksh（R34）。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 7.9 | prepared | 首次适配，待真机验证（Windows 阶段 2026-09-26 完成） |
