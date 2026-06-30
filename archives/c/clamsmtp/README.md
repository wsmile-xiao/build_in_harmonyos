# ClamSMTP

## 软件描述

ClamSMTP 是一个 SMTP 过滤代理，用于与 ClamAV 杀毒软件集成，实现邮件病毒扫描功能。它作为 SMTP 代理服务器，接收邮件后通过 ClamAV 进行病毒扫描，然后将干净的邮件转发到目标邮件服务器。

## 主要功能

- **病毒扫描**：与 ClamAV 集成，扫描通过 SMTP 协议传输的邮件
- **透明代理**：支持透明代理模式（需要 iptables/netfilter 支持）
- **标准代理**：支持标准 SMTP 代理模式
- **多线程**：支持多连接并发处理
- **灵活配置**：通过配置文件灵活设置监听地址、目标地址、超时等参数

## 当前支持的版本

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| 1.10 | built | 2026-05-28 |

## 编译说明

### 构建系统

- autotools (configure + make)

### 平台适配补丁

编译需要以下 3 个补丁：

1. **0001-common-smtppass.c.patch** (E091)
   - 解决 OHOS 头文件冲突问题
   - `linux/netfilter_ipv4.h` 与 `netinet/in.h` 结构体重复定义
   - 使用 `#ifdef __OHOS__` 守卫

2. **0003-config.guess.patch** (E007)
   - 平台识别修复
   - 添加 `aarch64:HarmonyOS:*:` 模式识别

3. **0004-configure-umask.patch** (E011)
   - HMDFS 权限限制修复
   - `umask 077` → `umask 022`

### 编译命令

```bash
./configure --prefix=$DEFAULT_PREFIX
make -j1
make install DESTDIR=$TEST_PREFIX
```

### 依赖

无外部依赖。仅需要标准 C 库和 pthread 支持。

## 使用说明

### 配置文件示例

```conf
# /etc/clamsmtpd.conf
OutAddress: 127.0.0.1:25
Listen: 127.0.0.1:10025
ClamAddress: /var/run/clamav/clamd.sock
User: clamav
```

### 运行命令

```bash
clamsmtpd -f /etc/clamsmtpd.conf
```

## 注意事项

1. **透明代理模式**：在 OHOS 上可能受限（iptables 支持情况未知）
2. **权限要求**：透明代理模式需要 root 权限
3. **ClamAV 配置**：需要预先配置好 ClamAV 的 clamd 服务
4. **安全弹窗**：首次运行二进制文件时可能需要确认弹窗（OHOS 已安装二进制可直接执行）

## 相关链接

- 官方网站：http://thewalter.net/stef/software/clamsmtp/
- 源码下载：http://thewalter.net/stef/software/clamsmtp/clamsmtp-1.10.tar.gz