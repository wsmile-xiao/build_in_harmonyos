# wmcore

> 把每个 CPU 核心的占用画成条形图的 X11 dockapp（Window Maker / libdockapp 家族）。

## 简介

wmcore 是一个 64×64 级别的停靠小应用：上半格显示整机平均占用，下半格按核心数逐行
画出每核占用条。它从 `/proc/stat` 采样（首轮 `cpu` 行是总计、之后每行一个核），
检测到的核数决定下半区的分格高度，因此 1 核到 20 核（`MAX_CPU`）都能自适应显示。

程序本身不含窗口管理协议特例——它通过 libdockapp 的 `openXwindow()` 建立
override-redirect 小窗并由宿主管道器（Window Maker、wmdock 类）负责嵌入，
所以在没有 X server 的环境里只能执行到 X 连接失败为止。

上游只有两个命令行开关：`-h`（打印 usage 后退出 0）与 `-d n`（每次刷新的微秒间隔，
默认 1000000）。没有配置文件、没有环境变量开关。

## OHOS 适配要点

- 这是 `package_type = "application"` 的包：不导出库，只交付 `bin/wmcore` 与
  `share/man/man1/wmcore.1`，命令行为由 `commands.json` 声明（R38）。
- 构建期三处鸿蒙特有处理（依据、症状与实测均在 `0.0.4/notes.md`）：
  1. **E386**：profile `[buildenv]` 导出的 `CONFIG_SHELL=/data/service/hnp/bin/bash`
     在 HMDFS 上 `getcwd()` 失败，autoconf 的 `configure` 会用 `$CONFIG_SHELL` 重新
     exec 自身并在启动期报 `working directory cannot be determined` ⇒ 在同一条
     shell 命令里 `unset CONFIG_SHELL`（`generate()` 期 unset 会被运行期重注入击败）。
  2. **E011/E114**：`config.status` 用 `(umask 077 && mktemp -d)` 建 scratch 目录，
     HMDFS 上该目录回读为 0660（无检索位）⇒ `can't create ./conffXXXXXX/subs1.awk:
     Permission denied`；在 `build()` 里把 `configure` 的 `umask 077` 就地改为 `022`。
  3. `AutotoolsDeps` 会把整条依赖闭包的 `-l` 塞进 `$LIBS`，autoconf 的第一个
     「运行程序」测试因此链接 X11 闭包；不注入 `LD_LIBRARY_PATH` 时会被误报成
     `cannot run C compiled programs / If you meant to cross compile, use --host`。
- OHOS clang 链接阶段已写入 `.codesign` 段，产物可直接执行，配方不再重复 self-sign；
  产物无 RPATH/RUNPATH，运行期依赖必须靠 Conan 的 `conanrun` 环境提供库路径。
- 已知未覆盖：dockapp 的窗口绘制与条形图刷新需要 X server（设备与 CI worker 都没有），
  本包只验证到「loader 放行、失败发生在 X 连接层」这一层，不宣称图形功能已验证。

## 依赖

| 依赖 | 版本 | 类型 | 说明 |
|------|------|------|------|
| libdockapp | 0.7.3 | 编译 + 运行 | `dockapp.pc`、`-ldockapp`、`libdockapp/wmgeneral.h` |
| libx11 | 6.4.0 | 编译 + 运行 | `X11/Xlib.h`、`-lX11`（传递 libxcb / libxau / libxdmcp / xorgproto / xtrans） |
| libxext | 6.4.0 | 编译 + 运行 | `X11/extensions/shape.h`、`-lXext` |
| libxpm | 3.5.17 | 编译 + 运行 | `X11/xpm.h`、`-lXpm` |

四个依赖都按已发布 `libdockapp/0.7.3` 自身的 6.4.0 轨声明，避免把 main 里另一套
`libxext/1.3.x` 拉进图里 fork 出第二套 X11 闭包。

## 功能验证

```bash
# 构建 + 消费者测试（13 条断言：9 条行为 + 4 条平台）
conan create archives/w/wmcore/0.0.4 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64

# 无头环境下可真实执行的两条路径（需带 Conan 运行库路径）
wmcore -h                     # 横幅 "wmcore 0.0.4 by bitman@bitmania.de" + usage，退出 0
DISPLAY=:99 wmcore            # "wmcore: can't open display :99"，退出 1（X 连接层，非加载器层）
```

## 参考

- [上游应用页](https://www.dockapps.net/wmcore)
- [官方源码分发](https://www.dockapps.net/download/wmcore-0.0.4.tar.xz)（sha256 `ecefdd49…34d20`）
- 版本级笔记：`0.0.4/notes.md`；验证补测（不入 PR，留盘证据）：`~/tmp/uc2/z63-wmcore/reports/conan-verify-supplement.md`
