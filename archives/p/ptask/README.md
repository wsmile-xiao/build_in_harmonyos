# ptask

## 简介

`ptask` 是 Jean-Philippe Orsini 开发的 **GTK+ 3 图形界面任务管理器**，作为命令行
任务管理器 [taskwarrior](https://taskwarrior.org/) 的前端使用：它读取
`task export` 的 JSON 输出，以树状视图按项目分组展示任务，并支持新建/修改/完成/删除
任务，另外可以为每个任务附加一段较长的备注（note）。

- 上游版本：1.0.0
- 许可证：GPL-2.0-or-later
- 上游站点：`wpitchoune.net`（已下线，存档见
  <https://web.archive.org/web/20160608075549/http://wpitchoune.net/blog/ptask/>）

> 注意：另有一个同名项目 `glipari/ptask`（Periodic Real-Time Task interface to
> pthreads，POSIX 实时周期任务库，最高版本 0.5），与本包**无关**。

## 功能概述

- 按项目分组的任务树，展示描述、优先级、标签、截止日期等字段
- 新建 / 修改 / 完成 / 删除任务，支持附加长备注
- 直接复用本机 taskwarrior 的数据（`task export` 的 JSON），不自己维护数据库
- 命令行入口：`ptask`（打开窗口）、`ptask --version`、`ptask --help`，以及本适配新增的
  无头 `ptask --selftest`

## 依赖

| 依赖 | 作用 |
|---|---|
| gtk/3.24.43 | GUI 工具包（鸿蒙构建启用 broadway 后端，无 X11 后端） |
| libx11/6.4.0、libxext/6.4.0 | `configure` 的 pkg-config 探测项（源码不调用 Xlib） |
| json-c/0.18 | 解析 `task export` 的 JSON |
| task/2.6.2 | 运行期必须存在 `task` 可执行文件（Taskwarrior） |

## 鸿蒙 PC 适配

- 发行包已带生成的 Autotools 文件，**无需 autoreconf**；共 7 个补丁，按下表编号：
  `0001`/`0002` config.guess/config.sub 识别 HarmonyOS、`0003` configure 临时目录 umask、
  `0004` `-Wl,--export-dynamic` 链接标志、`0005` 无头 `--selftest`、
  `0006` `trim()` 的 NUL 漏拷修复、`0007` json-c `is_error` 兼容 + taskwarrior 2.x 版本闸。
- 鸿蒙 PC 无 X server，GUI 窗口无法打开；`ptask --version/--help/--selftest`
  在打开 display 之前退出，因此可在容器内无头验证。
- 三条只有在本平台才暴露的坑（链接标志被 clang 当入口符号、glib 自带 libintl
  不在 `PkgConfigDeps` 的 `.pc` 里、`gio-2.0.pc` 缺自定义变量）记在
  [`1.0.0/notes.md`](1.0.0/notes.md)。

## 使用

```sh
conan install --requires=ptask/1.0.0
ptask            # 打开图形界面（需要可连接的显示后端与 Taskwarrior）
ptask --selftest # 无头自检（不打开窗口）
```

## 参考资料

- 上游源码发行物（发行版池副本）：
  <https://archive.ubuntu.com/ubuntu/pool/universe/p/ptask/ptask_1.0.0.orig.tar.gz>
- Debian 源包：`https://sources.debian.org/src/ptask/`
- Taskwarrior：<https://taskwarrior.org/>
- 本仓库适配笔记：[`1.0.0/notes.md`](1.0.0/notes.md)
