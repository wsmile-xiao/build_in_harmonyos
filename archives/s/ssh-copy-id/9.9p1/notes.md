# ssh-copy-id 9.9p1 编译笔记

## 编译信息
- 软件名称: ssh-copy-id
- 版本: 9.9p1
- 编译日期: 2026-05-28
- 编译状态: packaged
- 目标平台: OpenHarmony aarch64

## 特殊说明

### 软件类型
ssh-copy-id 是一个纯 Shell 脚本工具，无需编译，直接从源码打包即可。

### 源码来源
- 项目: OpenSSH
- 源文件: https://raw.githubusercontent.com/openssh/openssh-portable/master/contrib/ssh-copy-id
- 获取方式: 直接下载

### 依赖关系
运行时依赖：
- ssh (OpenSSH client)
- ssh-keygen (OpenSSH key generation tool)
- POSIX 兼容的 shell（sh/bash/dash/ksh）

### 安装要求
- 确保 OpenSSH 客户端已安装在系统中
- 脚本会自动检测可用的 shell 环境

### 平台适配
无需平台适配，脚本本身是跨平台的 POSIX shell 脚本。

### 测试验证
脚本安装后可通过以下命令验证：
```bash
ssh-copy-id -h
ssh-copy-id -n user@localhost  # 干运行模式测试
```

## 打包信息
- 打包格式: tar.gz
- 打包内容:
  - usr/local/bin/ssh-copy-id (可执行脚本)
  - usr/local/share/man/man1/ssh-copy-id.1 (可选，手册页)

## 注意事项
1. 脚本需要可执行权限（chmod +x）
2. 脚本第一行为 `#!/bin/sh`，确保系统有 /bin/sh
3. OpenHarmony 上已预装 GNU bash 5.3.0，脚本可正常运行
