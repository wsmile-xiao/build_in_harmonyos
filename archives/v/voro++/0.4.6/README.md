# voro++ 0.4.6 — OpenHarmony 预编译归档

## 软件简介

voro++ 是一个开源的三维 Voronoi 单元计算库，用于计算三维空间中点的 Voronoi 分解。主要功能：

- 容器类 Voronoi 计算（container, container_prd）
- 单个 Voronoi 单元计算
- 墙面限制的 Voronoi 区域
- 自定义输出格式
- 命令行工具 `voro++`

官方主页: http://math.lbl.gov/voro++/

## 编译信息

| 项目 | 值 |
|------|-----|
| 版本 | 0.4.6 |
| 构建系统 | Makefile + config.mk (自定义) |
| 编译器 | clang++ 15.0.4 |
| 目标架构 | aarch64 (OpenHarmony) |
| 编译日期 | 2026-06-03 |
| 状态 | published |

## 安装产物

| 文件 | 说明 |
|------|------|
| bin/voro++ | 命令行工具 (ELF64 aarch64) |
| lib/libvoro++.a | 静态库 (425KB) |
| include/voro++/*.hh | 14个 C++ 头文件 |
| man/man1/voro++.1 | man 手册页 |

## 补丁列表

1. **0001-Makefile.patch** — 添加 DESTDIR 支持，修复 install 目标路径
2. **0002-config.mk.patch** — 设置 clang++ 编译器和 -fPIC 选项
3. **0003-configure.patch** — 添加 configure wrapper 脚本（供 G0 clean-verify 使用）

## 使用方式

```bash
# 解压预编译包
tar xzf voro++-0.4.6-ohos-aarch64.tar.gz

# 查看版本
./bin/voro++ --version

# C++ 编程使用
#include "voro++/voro++.hh"
// 编译时链接: -lvoro++ -L./lib
```

## 注意事项

- 二进制版本号显示 "0.4.5"，但 NEWS 文件确认此版本为 0.4.6（上游版本号字符串未更新）
- 本库为纯静态库（libvoro++.a），无动态库
- dfsg1 源码包不含部分外部测试数据文件