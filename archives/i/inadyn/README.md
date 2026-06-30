# inadyn

## 软件简介

inadyn 是一个轻量级的动态DNS（Dynamic DNS）客户端，用于自动更新DNS记录。支持多个DNS服务提供商，包括：

- DynDNS
- FreeDNS
- ZoneEdit
- No-IP
- easyDNS
- DNS-O-Matic
- OpenDNS
- Namecheap
- HE.net (Hurricane Electric)
- Loopia
- Dyndns.it
- dnspod.cn

## 特性

- 跨平台支持（Linux、Windows、macOS、OpenHarmony）
- 支持HTTPS安全连接
- 支持IPv4和IPv6
- 轻量级设计，适合嵌入式设备
- 多账户支持
- 自定义DNS服务提供商支持

## OpenHarmony编译信息

### 编译版本
- **版本号**: 2.12.0-r0
- **编译日期**: 2026-05-21
- **编译状态**: built（静态编译）

### 编译配置
```bash
./configure --prefix=/storage/Users/currentUser/usr/local \
            --enable-openssl \
            --disable-shared \
            LDFLAGS="-static -Wl,-Bstatic"
```

### 关键依赖
- libconfuse/3.3
- openssl/1.1.1w

### 平台适配说明

OpenHarmony平台的musl libc动态链接器不完全支持RUNPATH，因此必须使用**静态编译**方案。主要适配工作：

1. **静态编译**: 使用LDFLAGS="-static"生成完全静态可执行文件
2. **HMDFS临时文件限制**: 修改config.status使用~/tmp和umask 022
3. **libtool静态链接失败**: 手动使用clang -static链接静态二进制

### 验证结果
```bash
$ file /storage/Users/currentUser/usr/local/sbin/inadyn
ELF executable, 64-bit LSB arm64, static, not stripped

$ /storage/Users/currentUser/usr/local/sbin/inadyn --version
2.12.0

$ ls -lh /storage/Users/currentUser/usr/local/sbin/inadyn
-rwxrwx--- 1 file_manager file_manager 4.1M inadyn
```

### 预编译包
- `inadyn-2.12.0-r0-ohos-aarch64.tar.gz` (2.9MB)
- 包含静态编译的可执行文件，可直接运行

## 使用方法

### 安装预编译包
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- inadyn 2.12.0-r0
```

### 配置文件
创建 `/etc/inadyn.conf`：
```conf
# 基本配置
system dyndns@dyndns.org
username your_username
password your_password
alias your_hostname.dyndns.org

# HTTPS支持
ssl

# 更新周期（秒）
period 300
```

### 运行
```bash
inadyn --config /etc/inadyn.conf
```

## 参考资料
- [官方仓库](https://github.com/troglobit/inadyn)
- [OpenHarmony编译归档](./2.12.0-r0/)