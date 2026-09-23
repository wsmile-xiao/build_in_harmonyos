# cheops — OpenHarmony 编译档案

## 软件简介
CHEOPS（**CHEss OPponent Simulator**，Tristan Miller 编写）是一个功能完整的 **console 象棋程序**：
支持 人/人、人/机、机/机 三种对弈方式，含 alpha-beta 搜索与 64 格棋盘显示，走子走标准代数记谱
（`e2e4`、`o-o`、`o-o-o`、`a7a8q`…）。许可证 GPL-3.0-or-later。本次适配上游发布版 **1.3**。
仅产出一个 `cheops` 可执行文件（控制台交互），无库、无头文件。

## OHOS 适配要点
- 2016 GNU autotools 递归工程（SUBDIRS=src+doc），产物为 `bin/cheops`、`man6/cheops.6` 与文档数据。
- 发布包**不随带 config.guess/config.sub** → 打包 FSF 2024 版（aarch64 已支持，技法同 ncmpcpp），
  在 build() 拷入源码根；configure 以 `--build=aarch64-unknown-linux-gnu` 固定三元组，
  跳过 config.guess（其无法识别 `uname -s=HarmonyOS`）。
- 源码 configure 内 `umask 077`→`umask 022`，TMPDIR 指到 conan build `_tmp`
  （HMDFS 临时目录组写权限问题，同 pakchois/p11-kit）。
- doc 的 PDF 生成在 `HAVE_PDFLATEX` 条件内——设备无 pdflatex 时自动跳过；man 页预生成直接安装。
- 纯 C++03、零外部依赖、无 `-Werror`；`validate()` os 白名单 Linux/OHOS（R32）。
  设备 profile `cppstd=17` 下 `ChessBoard.cpp` 唯一的 `register` 指示符（C++17 已移除）需去除。
- 上游**无任何自动化测试**（交互式程序）；不虚构，冒烟放 test_package：`--version`/`--help`
  退出码与 banner/usage，再加 `h/h + e2e4 + e7e5 + quit` 脚本化双人对局驱动真实游戏循环。

## 依赖关系
- 无编译/运行依赖（仅 C++ 运行时）
- 被依赖: 无（独立 CLI 程序）

## 参考资料
- [cheops 官方主页](https://logological.org/cheops)
- [cheops-1.3.tar.bz2](https://github.com/logological/cheops/releases/download/1.3/cheops-1.3.tar.bz2)
