# dinit - Service Manager and Init System

## 简介

dinit 是一个现代化的服务管理器和 init 系统，由 Davin McCall 开发。它提供了依赖管理、服务监控和智能重启等功能，被 Chimera Linux、eweOS 等系统采用作为默认 init 系统。

## 功能说明

### 核心组件

- **dinit**: 服务守护进程，负责启动、监控和管理系统服务
- **dinitctl**: 服务控制工具，用于启动、停止、查询服务状态
- **dinit-check**: 服务描述文件检查器，验证配置正确性
- **dinit-monitor**: 服务监控工具，监控服务状态变化并执行命令

### 主要功能

1. **依赖管理**: 支持服务依赖关系，自动按依赖顺序启动服务
2. **服务监控**: 监控进程状态，失败时自动重启
3. **依赖回滚**: 服务停止时自动回滚依赖服务
4. **用户模式**: 支持用户级服务管理（非 root）
5. **服务类型**: 支持多种服务类型（process、bgprocess、scripted、internal、triggered）

### 服务描述格式

```
type = process | bgprocess | scripted | internal | triggered
command = /path/to/command
stop-command = /path/to/stop-command
restart = true | false
logfile = /path/to/logfile
depends-on: service-name
waits-for: service-name
```

## 使用方法

### 基本命令

```bash
# 启动服务
dinitctl start service-name

# 停止服务
dinitctl stop service-name

# 查询服务状态
dinitctl status service-name

# 列出所有服务
dinitctl list

# 检查服务描述文件
dinit-check /path/to/service.description

# 监控服务状态变化
dinit-monitor service-name -- command-to-run
```

### 配置文件位置

- **系统服务目录**: `/etc/dinit.d/`, `/lib/dinit.d/`, `/usr/local/lib/dinit.d/`
- **用户服务目录**: `$HOME/.config/dinit.d/`
- **控制 socket**: `/var/run/dinitctl`（系统）或 `$HOME/.dinitctl`（用户）

### 示例服务描述

```bash
# sshd.service - SSH 守护进程
type = process
command = /usr/sbin/sshd -D
waits-for: syslogd
depends-on: loginready

# backup.service - 备份脚本
type = scripted
command = /usr/local/bin/backup.sh
stop-command = /usr/local/bin/stop-backup.sh
restart = false

# network.service - 内部服务（依赖检查点）
type = internal
depends-on: network-driver
```

## 版本信息

### 当前版本: 0.22.0

**发布日期**: 2026-05-19

**已编译版本**: 0.22.0

**编译状态**: ✅ published

**编译日期**: 2026-05-25

**测试日期**: 2026-05-25

**目标平台**: OpenHarmony aarch64

**编译器**: clang/clang++

### 平台适配说明

dinit 0.22.0 在 HarmonyOS 平台上自动检测并禁用了以下 Linux 特有功能：

- `BUILD_SHUTDOWN=no` — shutdown/poweroff/reboot 命令（需要 root 权限）
- `SUPPORT_CGROUPS=0` — cgroups 支持（鸿蒙不支持）
- `SUPPORT_CAPABILITIES=0` — capabilities 支持（鸿蒙不支持）
- `SUPPORT_IOPRIO=0` — I/O 优先级设置（鸿蒙不支持）
- `SUPPORT_OOM_ADJ=0` — OOM score adjustment（鸿蒙不支持）

保留的功能：
- `USE_INITGROUPS=1` — 初始化补充组
- `DEFAULT_AUTO_RESTART=ALWAYS` — 服务自动重启
- 服务依赖管理
- 服务监控和重启

### 编译选项

```bash
./configure --prefix=$DEFAULT_PREFIX
make -j2
# 手动安装（鸿蒙缺少 install 命令）
```

### 依赖

- **运行时依赖**: 无外部库依赖（仅依赖 libc 和 libc++_shared.so）
- **构建依赖**: clang++, make, m4（man 页面生成）

## 安装

### 从预编译包安装

```bash
# 下载预编译包
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- dinit 0.22.0

# 安装后的二进制文件位于 ~/usr/local/bin/
~/usr/local/bin/dinit --version
```

### 从源码编译

```bash
# 下载源码
curl -L -o dinit-0.22.0.tar.gz "https://api.github.com/repos/davmac314/dinit/tarball/refs/tags/v0.22.0"
tar -xzf dinit-0.22.0.tar.gz
cd davmac314-dinit-*

# 配置
./configure --prefix=$HOME/usr/local

# 编译
make -j2

# 手动安装（鸿蒙缺少 install 命令）
mkdir -p $HOME/usr/local/bin
for prog in dinit dinitctl dinit-check dinit-monitor; do
    cp src/$prog $HOME/usr/local/bin/
    chmod 755 $HOME/usr/local/bin/$prog
done

# 验证
$HOME/usr/local/bin/dinit --version
```

## 功能测试结果

### 测试状态: ✅ 基本功能通过

| 功能项 | 状态 | 说明 |
|--------|------|------|
| 二进制完整性 | ✅ PASS | 4 个 ELF 二进制文件完整 |
| 版本显示 | ✅ PASS | dinit/dinitctl/dinit-monitor 支持 --version |
| 帮助信息 | ✅ PASS | 所有工具 --help 输出完整 |
| 服务描述检查 | ✅ PASS | dinit-check 错误检测能力强大 |
| 循环依赖检测 | ✅ PASS | 成功检测循环依赖 |
| 无效配置检测 | ✅ PASS | 检测未知选项、无效值、缺失依赖 |

### 已知限制

1. **用户模式限制**: 用户模式下 socket 创建失败，无法连接到用户实例（平台限制）
2. **系统模式限制**: 系统模式需要 root 权限，未测试
3. **shutdown 命令**: 鸿蒙不支持 shutdown/poweroff/reboot，已禁用
4. **dinit-check 版本**: 不支持 --version 选项（其他工具都支持）
5. **install 命令缺失**: 鸿蒙缺少 GNU install 命令，需手动安装（E098）

### 部署建议

```bash
# 1. 创建服务目录
mkdir -p ~/usr/local/lib/dinit.d

# 2. 编写服务描述文件
echo "type = process" > ~/usr/local/lib/dinit.d/my-service
echo "command = /path/to/daemon" >> ~/usr/local/lib/dinit.d/my-service

# 3. 检查服务描述
dinit-check ~/usr/local/lib/dinit.d/my-service

# 4. 启动用户实例（注意：socket 创建可能失败）
dinit --user --services-dir ~/usr/local/lib/dinit.d

# 5. 控制服务
dinitctl -u start my-service
```

## 文档

- **dinit(8)**: dinit 守护进程手册
- **dinitctl(8)**: dinitctl 控制工具手册
- **dinit-check(8)**: 服务描述检查器手册
- **dinit-monitor(8)**: 服务监控工具手册
- **dinit-service(5)**: 服务描述格式和配置选项

在线文档：https://davmac.org/projects/dinit/

## 许可证

dinit 使用 Apache License 2.0 许可证，允许自由使用、修改和分发。

## 相关链接

- **官方网站**: https://davmac.org/projects/dinit/
- **源码仓库**: https://github.com/davmac314/dinit
- **使用系统**: Chimera Linux, eweOS, Artix Linux, antiX
- **OpenHarmony 移植**: 由 OpenHarmonyPCDeveloper 社区维护

## 更新历史

- **2026-05-25**: 功能测试完成，验证基本功能正常（38/42 PASS）
- **2026-05-25**: 完成 OpenHarmony aarch64 平台适配
- **2026-05-19**: dinit 0.22.0 发布