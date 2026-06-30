# vbindiff 3.0_beta5 — OpenHarmony 预编译包

VBinDiff (Visual Binary Diff) 是一个基于 ncurses 的交互式终端工具，用于可视化比较两个二进制文件。

## 基本信息

| 字段 | 值 |
|------|-----|
| 软件 | vbindiff |
| 版本 | 3.0_beta5 |
| 状态 | built |
| 构建系统 | autotools |
| 编译器 | clang / clang++ |
| 目标平台 | OpenHarmony aarch64 (ELF64 PIE) |
| 编译日期 | 2026-06-02 |
| 源码 | https://github.com/madsen/vbindiff/archive/e478092.tar.gz |

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| ncurses | 6.4 | 静态链接 (libncursesw.a)，运行时无动态依赖 |
| libc++_shared.so | OHOS 系统库 | 运行时依赖 |
| libc.so | OHOS 系统库 | 运行时依赖 |

## 使用方法

```bash
# 安装
tar xzf vbindiff-3.0_beta5-ohos-aarch64.tar.gz -C /usr/local

# 单文件查看
vbindiff FILE1

# 双文件对比
vbindiff FILE1 FILE2

# 版本查看
vbindiff --version

# 帮助信息
vbindiff --help
```

## 预编译包内容

- `bin/vbindiff` — ELF64 PIE 可执行文件 (317KB)
- `share/man/man1/vbindiff.1` — 手册页

## 应用补丁

源码需要应用以下 2 个补丁后才能编译：

1. `0001-config.h.in.patch` — autotools configure 生成的配置头文件变更（平台适配）
2. `0002-curses-ConWin.hpp.patch` — 添加 `#undef clear` 和 `#undef move` 防止 ncurses 宏与 C++ 成员函数冲突

## 注意事项

- vbindiff 是交互式终端应用，依赖 ncurses TUI 界面，需要真实终端环境运行
- ncurses 以静态方式链接，运行时仅需 OHOS 系统库 (libc++_shared.so, libc.so)
- 版本号 3.0_beta5 为开发测试版本，非正式稳定发布版