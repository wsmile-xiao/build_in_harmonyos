# pumba

**Chaos testing tool for Docker, containerd, and Podman containers**

## 简介

Pumba 是一个混沌测试和网络模拟工具，用于 Docker、containerd 和 Podman 容器。受 Netflix Chaos Monkey 启发，Pumba 将混沌工程带到容器级别——可以 kill、stop、pause 和 remove 容器，注入网络延迟和丢包，或者压力测试容器资源。

## 功能特性

- **容器生命周期混沌**: kill、stop、pause、remove 容器
- **网络混沌**: 注入网络延迟、丢包、带宽限制
- **资源压力测试**: stress-ng 集成，压力测试 CPU、内存、IO
- **多运行时支持**: Docker、containerd、Podman
- **Slack 集成**: 支持通过 Slack 发送混沌事件通知

## 编译状态

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 1.1.2 | ✅ built | 2026-06-04 | 在 /data/storage/el2/base/cache 目录编译成功，绕过 HMDFS SELinux 限制 |

## 编译说明

### 构建系统

- **类型**: Makefile + Go
- **编译器**: Go >= 1.25.0
- **依赖**: 无外部依赖（Go 模块自包含）

### 平台限制

⚠️ **重要**: Go 项目在 HMDFS 文件系统上受 SELinux 权限限制，无法编译。

**错误信息**:
```
link: mapping output file failed: permission denied
```

**原因**: HMDFS 的 SELinux 强制访问控制(MAC)策略限制了 Go link 工具的某些操作(mmap、临时文件创建、文件映射)。

**解决方案**:
1. 在其他环境（非 HMDFS）编译
2. 等待鸿蒙系统 SELinux 策略更新
3. 使用预编译二进制包（如果有）

参见知识条目 E103: Go link 工具在 HMDFS 上 SELinux 权限限制

### 编译步骤（推荐方法）

```bash
# 1. 安装 Go 1.26.0+
# 2. 配置 GOPROXY
export GOPROXY=https://goproxy.cn,direct

# 3. 在 cache 目录编译（绕过 HMDFS SELinux 限制）
mkdir -p /data/storage/el2/base/cache/build-pumba
cd /data/storage/el2/base/cache/build-pumba
cp -r ~/builds/pumba-1.1.2.work/* .
export TMPDIR=/data/storage/el2/base/cache/tmp
export GOCACHE=/data/storage/el2/base/cache/tmp/go-cache
go build -v -o pumba ./cmd

# 4. 签名并验证
ohc-run.py sign-elf pumba
./pumba --version
```

### 关键发现

**解决方案**: 在 `/data/storage/el2/base/cache` 目录编译可以绕过 HMDFS SELinux 限制。

该目录可能在不同的文件系统上，SELinux 策略更宽松，允许 Go link 工具正常工作。所有 Go 项目推荐使用此方法编译。

## 来源

- **GitHub**: https://github.com/alexei-led/pumba
- **版本**: 1.1.2 (master 分支)
- **许可证**: Apache 2.0

## 相关知识

- **E103**: Go link 工具在 HMDFS 上 SELinux 权限限制
- **E046**: chmod 不生效 SELinux 限制（类似平台限制）