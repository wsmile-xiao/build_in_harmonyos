# lcs

## 简介
Liberal Crime Squad（LCS）是一个讽刺题材的终端 roguelike 游戏：玩家指挥一支"自由主义犯罪小队"，通过行动影响舆论与立法，最终推动自由主义议程。SourceForge 上由开源社区维护（源自 Tarn Adams / Bay 12 Games 的 3.9 版本）。

## 主要功能
- 终端 roguelike 玩法：招募、行动、庭审、立法全流程
- ncurses 全屏界面（宽字符/Unicode）
- 基于可配置文件的数据驱动（vehicles/clips/weapons/armors/masks/loot/creatures 七类 XML + sitemaps.txt）

## OHOS 适配
- 构建系统：Autotools（`autoreconf -fvi` 引导）
- 目标架构：aarch64-linux-ohos（musl + libc++）
- 依赖：ncurses/6.5（平铺头布局，补丁让上游探测接受平铺 ncursesw）
- 版本：4.07.4b = SourceForge SVN r738（无官方 tarball，逐文件固定修订下载）

## 依赖
- ncurses（宽字符，静态）

## 功能验证
```bash
crimesquad
# 标题画面出现后按 ESC 退出（"Press ESC now to quit"）
```

## 参考
- 主页：https://sourceforge.net/projects/lcsgame/
- 源码：https://svn.code.sf.net/p/lcsgame/code/ (r738)
