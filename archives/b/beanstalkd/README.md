# beanstalkd

## 软件信息
- **名称**: beanstalkd
- **版本**: 1.13
- **描述**: 一个简单、快速的工作队列服务

## 功能说明
beanstalkd 是一个轻量级的消息队列系统，设计目标是快速、高效地处理后台任务。

主要特性：
- 支持多个队列（tube）
- 任务优先级管理
- 任务延迟和超时设置
- 持久化支持（通过 write-ahead log）
- 简单的协议（基于文本）
- 高性能（单进程、事件驱动）

## 编译状态
- **状态**: published
- **编译日期**: 2026-06-06
- **构建系统**: makefile
- **编译器**: clang/clang++

## 已编译版本
| 版本 | 状态 | 编译日期 | 备注 |
|------|------|----------|------|
| 1.13 | published | 2026-06-06 | 平台适配完成，通过基本功能验证，已生成预编译包 |

## 平台适配说明
HarmonyOS 基于 Linux 内核，使用 epoll API。通过创建 `harmonyos.c -> linux.c` 软链接实现平台适配。

## 来源
- 官方网站: https://beanstalkd.github.io/
- 源码仓库: https://github.com/beanstalkd/beanstalkd