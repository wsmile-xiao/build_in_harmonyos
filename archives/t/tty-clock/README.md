# tty-clock

**基于 ncurses 的终端数字时钟**

tty-clock 是一个使用 ncurses 库在终端中显示数字时钟的简单程序。它以可配置的格式显示当前时间和日期，并提供多种显示选项。

## 功能特性
- 终端中显示当前时间（ncurses 渲染）
- 12小时/24小时格式切换
- 秒数显示选项（-s）
- 居中显示模式（-c）
- 屏保模式（-S）
- 自定义颜色方案（-C [0-7]）
- 粗体/闪烁选项（-b/-B）
- UTC 时间模式（-u）
- 自定义日期格式（-f）
- 冒号闪烁效果（-B）

## 编译版本
- **2.3**（为 OpenHarmony aarch64 编译）

## 依赖
- ncurses 6.4（静态链接，使用 --without-shared 编译）

## 重要说明
- ncursesw 静态链接内置了 stale staging terminfo 路径，需创建 symlink 修复：
  `mkdir -p ~/tmp/test-install-ncurses-6.4/share && ln -s ~/usr/local/share/terminfo ~/tmp/test-install-ncurses-6.4/share/terminfo`
- 修复后可直接运行，无需设置任何环境变量

## 使用方法
```bash
tty-clock -v    # 版本信息
tty-clock -i    # 软件信息
tty-clock -h    # 帮助页面
tty-clock -s    # 显示秒数
tty-clock -c    # 居中显示
tty-clock -u    # UTC时间
tty-clock -B    # 闪烁冒号
```