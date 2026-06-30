# dnstracer

DNS 追踪工具 - 用于追踪 DNS 解析路径，显示从本地 DNS 服务器到权威 DNS 服务器之间的查询链路。

## 项目信息

- **上游项目**: http://www.mavetju.org/unix/dnstracer.php
- **版本**: 1.9
- **许可**: BSD License

## 功能特性

- ✅ DNS 解析路径追踪
- ✅ 支持多种查询类型（A、AAAA、MX、NS、CNAME、TXT、SOA 等）
- ✅ 自动检测系统 DNS 服务器配置
- ✅ 支持指定 DNS 服务器进行追踪
- ✅ 显示详细的 DNS 查询过程
- ✅ 支持缓存控制选项

## OpenHarmony 适配

### 适配状态

- **编译状态**: ✅ 成功
- **功能状态**: ✅ 完全可用（修复后）
- **测试覆盖率**: 100%
- **质量门禁**: G0-G4 全部通过

### 适配版本

| 版本 | 编译日期 | 状态 | 补丁 | 说明 |
|------|---------|------|------|------|
| 1.9 | 2026-05-29 | published | 0001-dnstracer.c.patch | 所有功能已修复，完全可用 |

### 适配说明

**musl libc 兼容性修复**：
- 实现手动读取 `/etc/resolv.conf` 的 DNS 服务器检测功能
- 替代 glibc `_res` 结构方法（musl libc 不支持）

**查询类型选项修复**：
- 使用大小写不敏感的字符串比较（strcasecmp）
- 支持用户输入大写或小写查询类型名

### 已知问题

**无** - 所有已知问题已修复并验证。

## 使用方法

### 基本用法

```bash
# DNS 解析路径追踪（自动检测 DNS 服务器）
dnstracer example.com

# 指定 DNS 服务器
dnstracer -s 8.8.8.8 example.com

# 查询 MX 记录
dnstracer -s 8.8.8.8 -q MX example.com

# 查询 NS 记录
dnstracer -s 8.8.8.8 -q NS example.com
```

### 常用选项

- `-s <server>`: 指定 DNS 服务器（如 8.8.8.8、1.1.1.1）
- `-q <type>`: 指定查询类型（A、MX、NS、CNAME、TXT、SOA 等，大小写不限）
- `-o`: 显示概述模式
- `-c`: 禁用本地缓存
- `-4`: 仅使用 IPv4
- `-r <retries>`: 设置重试次数
- `-t <timeout>`: 设置超时时间

### 查询类型

支持以下查询类型（大小写不敏感）：
- A: IPv4 地址
- AAAA: IPv6 地址
- MX: 邮件交换记录
- NS: 名称服务器
- CNAME: 别名记录
- TXT: 文本记录
- SOA: 授权起始记录
- PTR: 反向解析

## 安装方法

### 通过预编译包安装

```bash
# 从 cmd-pkgs 仓库下载预编译包
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- dnstracer 1.9
```

### 手动编译

```bash
# 下载源码
wget http://deb.debian.org/debian/pool/main/d/dnstracer/dnstracer_1.9.orig.tar.gz

# 解压并应用补丁
tar -xzf dnstracer_1.9.orig.tar.gz
cd dnstracer-1.9
patch -p1 < 0001-dnstracer.c.patch

# 编译
./configure --prefix=$HOME/usr/local
make
make install
```

## 测试验证

### 功能测试

所有功能测试通过（100% 覆盖率）：

- ✅ DNS 追踪功能
- ✅ 查询类型选项
- ✅ DNS 服务器自动检测
- ✅ 概述模式
- ✅ 缓存控制
- ✅ IPv4 only 模式
- ✅ 错误处理

详细测试报告见：`reports/test-report.md`

### 质量门禁

- G0: 干净构建验证 ✅
- G1: 二进制完整性 ✅
- G2: 功能可用性 ✅
- G3: 可移植性（RPATH/签名） ✅
- G4: 归档完整性 ✅

## 补丁说明

补丁文件：`0001-dnstracer.c.patch`

**修复内容**：
1. DNS 服务器自动检测：实现手动读取 `/etc/resolv.conf`
2. 查询类型大小写不敏感：使用 `strcasecmp` 替代 `strcmp`
3. 跨平台兼容性：添加必要的头文件和宏定义

**补丁统计**：+51 行，-15 行，净增 36 行

## 依赖关系

**无外部依赖** - 仅需要标准 C 库和 DNS 解析库。

## 参考资料

- [上游项目主页](http://www.mavetju.org/unix/dnstracer.php)
- [编译测试报告](./1.9/reports/test-report.md)
- [适配笔记](./1.9/notes.md)

---

**维护者**: OpenHarmony PC Developer Team
**最后更新**: 2026-05-29