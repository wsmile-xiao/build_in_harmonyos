# dhcping

## 简介

dhcping 是一个 DHCP 服务器测试工具，用于验证 DHCP 服务器是否能够正确响应 DHCP 请求。它发送 DHCP DISCOVER/REQUEST/INFORM 等消息，并等待服务器响应。

## 主要功能

- **DHCP 服务器检测**：验证 DHCP 服务器的可达性和响应能力
- **响应时间测试**：测量 DHCP 请求的响应延迟
- **多种请求类型**：支持 DISCOVER、REQUEST、INFORM 等消息类型
- **灵活参数配置**：可指定服务器地址、客户端 MAC、超时时间等

## OHOS 适配要点

### 平台识别
dhcping 1.2 是 2002 年发布的软件，原始的 `config.guess` 无法识别 HarmonyOS 系统。需要更新为最新版本（2021+）并添加 HarmonyOS 识别规则：

```bash
# config.guess 添加以下规则
aarch64:HarmonyOS:*:*)
    echo "$UNAME_MACHINE"-unknown-linux-gnu
    exit ;;
```

### HMDFS 文件系统限制
configure 脚本在 HarmonyOS 的 HMDFS 文件系统上创建临时文件可能失败。解决方案：
- 手动编译 dhcping.c（绕过 configure）
- 直接使用 cc 编译并链接

### 权限要求
dhcping 需要访问原始套接字（raw socket），因此：
- 必须以 root 权限运行
- 或安装为 setuid root（不推荐，有安全风险）

## 依赖关系

- **编译依赖**：无（纯 C 程序，仅依赖标准库）
- **运行依赖**：需要网络访问权限

## 已知问题

1. **编译警告**：42 个类型不匹配警告（unsigned char[] vs char*），老代码常见问题，不影响功能
2. **权限限制**：必须 root 或 setuid root 才能正常运行
3. **无自动化测试套**：建议手动测试 DHCP 服务器检测功能

## 参考资料

- Debian 软件包：https://packages.debian.org/dhcping
- 源码下载：https://deb.debian.org/debian/pool/main/d/dhcping/