# iputils 20240905 发布说明

## 版本信息

- **发布日期**: 2024-09-05
- **编译日期**: 2026-05-06
- **平台**: HarmonyOS aarch64
- **状态**: ✅ 编译成功，功能验证通过

## 新特性

### IPv4/IPv6 统一工具

iputils 20240905 最重要的改进是统一了 IPv4 和 IPv6 工具：

- **ping**: 单一工具支持 IPv4 和 IPv6（替代传统的 ping + ping6）
- **tracepath**: 单一工具支持 IPv4 和 IPv6（替代传统的 tracepath + traceroute6）

用户可以通过 `-4` 或 `-6` 选项明确指定协议，或让工具自动选择。

### 其他改进

- 移除了 obsolete 工具（ninfod, rarpd, rdisc, tftpd）
- 改进的 meson 构建系统
- 更好的代码质量和错误处理

## HarmonyOS 适配

本次编译针对 HarmonyOS/musl 平台进行了以下适配修复：

### 修复 1: program_invocation_short_name 支持

- 问题: glibc 特有变量，musl 不支持
- 解决: 使用 __progname 替代
- 影响: error() 函数定义

### 修复 2: sockaddr_storage 重定义

- 问题: sys/socket.h 和 linux/socket.h 重复定义
- 解决: 使用宏重命名避免冲突
- 影响: arping.c 头文件包含顺序

## 功能验证

所有工具在 HarmonyOS 平台上通过功能验证：

- ✅ ping IPv4/IPv6: 正常工作
- ✅ tracepath IPv4/IPv6: 正常工作
- ✅ arping: 版本信息正确
- ✅ clockdiff: 版本信息正确

## 已知限制

1. **capability 支持**: 已禁用（需要 root 权限或手动设置）
2. **IDN 支持**: 已禁用（不支持国际化域名）
3. **国际化**: 已禁用（仅支持英文消息）
4. **ELF 签名**: 未签名（需要在打包时处理）

## 安装说明

使用预编译包中的 install.sh 脚本：

```bash
tar xzf iputils-20240905-ohos-aarch64.tar.gz
./install.sh
```

## 更新历史

- 2026-05-06: HarmonyOS aarch64 预编译版本发布
- 2024-09-05: iputils 20240905 官方版本发布