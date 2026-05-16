# autossh 1.4g

## 软件简介

autossh 是一个自动重启 SSH 会话和隧道的工具。它监控 SSH 连接的状态，当连接断开或停止传递数据时自动重启 SSH 进程。

**版本**: 1.4g (最新稳定版，2019-01-05 发布)
**作者**: Carson Harding (harding@motd.ca)
**官网**: https://www.harding.motd.ca/autossh/

## 功能特性

1. **SSH 会话监控**: 通过端口转发或 echo 服务监控 SSH 会话状态
2. **自动重启**: 当 SSH 进程异常退出时自动重启
3. **智能退出**: 正常退出（如用户输入 exit）时不会重启
4. **信号处理**: 支持 SIGTERM/SIGINT 优雅退出，SIGUSR1 强制重启
5. **后台运行**: 支持 `-f` 参数后台运行
6. **配置灵活**: 通过环境变量配置行为

## 编译信息

- **构建系统**: autotools (configure + Makefile)
- **编译器**: clang 15.0.4
- **目标架构**: aarch64 (ARM 64-bit)
- **链接方式**: 静态链接
- **依赖**: ssh (OpenSSH 9.6p1)
- **二进制大小**: 70KB

## 安装方法

### 使用预编译包

```bash
# 下载预编译包
wget autossh-1.4g-ohos-aarch64.tar.gz
wget install-autossh-1.4g.sh

# 安装
chmod +x install-autossh-1.4g.sh
./install-autossh-1.4g.sh

# 验证
autossh -V
```

### 手动安装

```bash
tar xzf autossh-1.4g-ohos-aarch64.tar.gz
cp -r usr/local/* ~/usr/local/
```

## 使用方法

### 基本用法

```bash
# 简单用法：监控 SSH 会话
autossh -M 20000 user@remote_host

# 禁用监控（依赖 SSH 内置保活）
autossh -M 0 -o ServerAliveInterval=15 -o ServerAliveCountMax=3 user@remote_host

# 后台运行
autossh -f -M 0 user@remote_host
```

### 环境变量配置

```bash
# 检查间隔（秒）
export AUTOSSH_POLL=30

# 启动门控时间（秒）
export AUTOSSH_GATETIME=15

# 最大重启次数
export AUTOSSH_MAXSTART=10

# 最大生命周期（秒）
export AUTOSSH_MAXLIFETIME=3600

# 日志文件
export AUTOSSH_LOGFILE=/var/log/autossh.log

# SSH 路径（如果不在默认位置）
export AUTOSSH_PATH=/usr/bin/ssh
```

### 常用场景

#### 1. 维持 SSH 隧道

```bash
# 本地端口转发隧道
autossh -M 20000 -f -N -L 8080:localhost:80 user@server

# 远程端口转发隧道
autossh -M 20000 -f -N -R 8080:localhost:80 user@server
```

#### 2. 长时间远程连接

```bash
# 保持远程会话
autossh -M 0 -o ServerAliveInterval=30 -o ServerAliveCountMax=3 user@server
```

#### 3. 启动脚本示例

```bash
# /etc/init.d/autossh 或 systemd service
#!/bin/sh
export AUTOSSH_POLL=60
export AUTOSSH_GATETIME=30
export AUTOSSH_LOGFILE=/var/log/autossh.log
autossh -M 0 -f -N -L 8080:localhost:80 user@server
```

## 文件结构

```
usr/local/
├── bin/
│   └── autossh              # 主程序
├── share/
│   ├── doc/autossh/
│   │   ├── CHANGES          # 更新日志
│   │   └── README           # 说明文档
│   ├── examples/autossh/
│   │   ├── autossh.host     # 示例包装脚本
│   │   └── rscreen          # rscreen 示例
│   └── man/man1/
│       └── autossh.1        # man page
```

## 注意事项

1. **SSH 配置**: 使用前确保 SSH 密钥认证已配置（无密码登录）
2. **监控端口**: `-M` 指定的端口不应被其他程序使用
3. **防火墙**: 监控端口需要在防火墙中开放（如使用 echo 服务）
4. **调试**: 设置 `AUTOSSH_DEBUG=1` 可启用详细日志

## 参考文档

- **项目主页**: https://www.harding.motd.ca/autossh/
- **Man page**: `man autossh` 或查看 `autossh.1` 文件
- **示例脚本**: `autossh.host` 和 `rscreen`
- **编译报告**: archives/a/autossh/1.4g/reports/test-report.md

## 编译来源

- **源码包**: https://www.harding.motd.ca/autossh/autossh-1.4g.tgz
- **归档目录**: /storage/Users/currentUser/.opendesk/apps/skills/resources/openharmony-compile-agent/archives/a/autossh/1.4g/

---

**编译日期**: 2026-05-15
**编译状态**: partial → success
**分发状态**: 可用