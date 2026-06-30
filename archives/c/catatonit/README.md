# catatonit

## 简介
catatonit 是一个轻量级的容器 init 系统，用于在容器中作为 PID 1 进程运行，负责信号转发和孤儿进程回收。它是 tini 的一个分支，专为容器环境设计。

## 功能
- 作为容器的 PID 1 进程运行
- 转发信号给子进程
- 回收孤儿进程
- 防止僵尸进程

## 版本
- **0.2.1** (2026-05-26) - 编译成功，静态编译

## 依赖
无外部依赖（静态编译）

## 平台适配说明
- musl 平台需应用补丁：0001-catatonit.c.patch（将 secure_getenv 替换为 getenv）
- tmpfs/HMDFS 平台 configure 有限制，需手动编译

## 使用
```bash
# 安装
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- catatonit 0.2.1

# 验证
catatonit --version
```