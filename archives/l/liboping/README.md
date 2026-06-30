# liboping

## 简介

liboping 是一个轻量级的 C 语言网络 ping 操作库，提供简单易用的 API 用于执行 ICMP ping 请求。

## 功能概述

- 提供 C 语言 API 用于发送和接收 ICMP echo 请求
- 支持同步和异步 ping 操作
- 支持多主机并行 ping
- 提供 Perl 和 Python 绑定（可选）
- 包含 oping 命令行工具

## OHOS 适配要点

1. **平台识别**：需要更新 config.guess/config.sub 补丁以正确识别 HarmonyOS 平台
2. **autoreconf**：原始 configure 脚本为 2013 年版本，需要重新生成以兼容现代 autotools
3. **raw socket 权限**：oping 工具需要 raw socket 权限，安装后需设置：
   ```bash
   setcap cap_net_raw=ep $PREFIX/bin/oping
   ```
4. **ncurses 未安装**：noping（ncurses 版本）未编译，仅编译了基础 oping 工具

## 依赖关系

- **编译依赖**：无外部依赖
- **运行依赖**：无外部依赖

## 参考资料

- 官网：https://noping.org
- 源码：https://github.com/octo/liboping