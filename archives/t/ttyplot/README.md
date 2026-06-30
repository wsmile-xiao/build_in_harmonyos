# ttyplot

ttyplot 是一个终端实时绘图工具，从标准输入读取数据并绘制实时折线图。适用于监控 CPU 使用率、网络流量、温度等指标的场景。

## 功能概述

- 从 stdin 读取数值数据，实时绘制折线图
- 支持单通道和双通道（`-2` 参数）绘图模式
- 支持速率模式（`-r` 参数），将计数器值除以采样间隔
- 可自定义绘图字符（`-c` 参数）
- 可设置标题（`-t`）、单位（`-u`）、初始最大值（`-s`）等参数
- 支持颜色设置（`-C` 参数）
- 支持硬限制模式（`-m` 上限、`-M` 下限）
- 实时显示 last、min、max、avg 统计信息
- ncurses 终端界面，支持交互式热键操作（q 退出、r 切换速率模式）

## OHOS 适配要点

- **构建系统**：plain Makefile（非 autotools），无 configure 步骤
- **ncursesw 依赖**：ncurses 预编译包（--without-shared）未提供 .pc pkg-config 文件，需手动创建 ncursesw.pc 和 ncurses.pc 在 `$DEFAULT_PREFIX/lib/pkgconfig/` 目录
- **宽字符支持**：ncursesw.pc 的 Cflags 需包含 `-D_XOPEN_SOURCE_EXTENDED`
- **编译警告**：`mvvline_set` 函数声明警告（4个），ncursesw wide-char API 在当前环境下头文件中未完全声明，不影响功能
- **版本标志**：ttyplot 使用 `-v` 参数输出版本号，不支持 `--version`
- **交互式程序**：ttyplot 是终端交互程序，需要 ncurses 终端环境，管道测试需用 `timeout` 控制

## 依赖关系

### 编译依赖
- ncurses/6.4（预编译包，--without-shared 静态编译）

### 运行依赖
- ncurses（终端界面渲染）
- musl libc（动态链接）

## 参考资料

- 官网：https://github.com/tenox7/ttyplot
- 源码仓库：https://github.com/tenox7/ttyplot
- 许可证：Apache-2.0