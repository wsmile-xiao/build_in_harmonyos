# lockrun

> Run cron jobs with overrun protection

## 简介

lockrun 是一个用于防止 cron 任务重叠执行的小型工具。它通过文件锁机制确保同一时间只有一个实例在运行，避免因前一次执行尚未完成而再次启动导致的问题。

该工具主要用于 cron 环境中，当定时任务的执行时间可能超过调度间隔时，lockrun 可以有效防止任务堆积和资源浪费。

## OHOS 适配要点

- lockrun 是单文件 C 程序（lockrun.c），无标准构建系统（无 configure/make/Makefile）
- 需要手动使用 clang 编译
- 源码使用了 flock() 系统调用，需要确认鸿蒙平台支持
- 使用 public domain 许可证

## 排除与替代

无特殊排除项。该工具为独立命令行程序，无可选组件。

## 依赖

无外部依赖。lockrun 是纯 C 程序，仅依赖标准 C 库和 POSIX flock() 系统调用。

## 功能验证

```bash
# 显示帮助信息
lockrun

# 基本使用示例
lockrun --lockfile=/tmp/myjob.lock -- my_command_here
```

## 参考

- [官方网站](https://unixwiz.net/tools/lockrun.html)
- [作者](https://www.unixwiz.net/)
