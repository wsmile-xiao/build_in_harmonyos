# Open MPI

Open MPI 是一个高性能消息传递库，实现了 MPI（Message Passing Interface）标准，广泛用于并行计算和分布式计算场景。

## 功能概述

- **MPI 标准实现**：完整支持 MPI-3.1 标准
- **高性能通信**：优化的点对点和集合通信
- **多网络支持**：TCP、共享内存、Infiniband 等
- **进程管理**：灵活的进程启动和监控
- **故障恢复**：支持进程故障检测和恢复

## OHOS 适配要点

### 已解决的问题

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| rindex 符号未定义 | musl libc 不提供 rindex() | 添加 `#define rindex strrchr` |
| 平台识别 | config.guess 需支持 ohos | 已内置支持 |

### 特殊说明

- Open MPI 自带 libevent 和 hwloc 组件，无需额外编译依赖
- 编译时间较长（约 25 分钟），建议使用 `-j1` 避免并发问题
- 目标平台正确识别为 `aarch64-unknown-linux-ohos`

## 依赖关系

### 编译依赖
- 无外部依赖（自带 libevent 和 hwloc）

### 运行依赖
- 无必需依赖

## 快速安装

```bash
# 从 cmd-pkgs 安装
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- open-mpi 5.0.10

# 验证安装
mpirun --version
ompi_info
```

## 基本信息

| 项目 | 值 |
|------|-----|
| 版本 | 5.0.10 |
| MPI API | 3.1.0 |
| 目标平台 | aarch64-unknown-linux-ohos |
| 预编译包大小 | 101MB |
| 调试符号包 | 13MB |

## 参考资料

- 官网: https://www.open-mpi.org
- 文档: https://www.open-mpi.org/doc/
- 源码: https://github.com/open-mpi/ompi