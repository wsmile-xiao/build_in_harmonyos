# complexity

GNU complexity — measures the complexity of C source code, weighting line
counts by logic-level nesting. Ships the `complexity` analyzer binary and
the `cx-vs-mc` helper script.

## 项目信息

- **官方仓库**: https://www.gnu.org/software/complexity/
- **源码下载**: https://ftp.gnu.org/gnu/complexity/
- **许可证**: GPL-3.0-or-later
- **语言**: C
- **构建系统**: autotools

## 版本历史

- **1.13**: 首次适配 OHOS 平台

## 适配说明

1. 显式 `--build/--host` triplet 绕过 config.guess 受限文件系统探测问题
2. `SHELL` 指向 bash 以满足 configure 与 automake test-driver 的语法需求
3. 上游 automake 测试套件（`make check`）在配方内完整执行并解析计数
