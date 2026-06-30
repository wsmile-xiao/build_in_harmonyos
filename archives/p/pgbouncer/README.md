# pgbouncer

PgBouncer 是 PostgreSQL 的轻量级连接池，用于减少连接开销并提高数据库性能。

## 基本信息

- **版本**: 1.22.1
- **构建系统**: autotools
- **编译日期**: 2026-05-27
- **状态**: built

## 描述

PgBouncer 是一个高效的 PostgreSQL 连接池管理器，通过复用连接来降低数据库负载，特别适用于高并发场景。

## 已编译版本

| 版本 | 状态 | 预编译包 | 补丁数 |
|------|------|----------|--------|
| 1.22.1 | built | ✅ | 4 |

## 依赖

- openssl/3.5.6
- libevent/2.1.12
- c-ares/1.34.4

## 编译要点

### 平台适配（E007/E072）
- config.guess 需添加 HarmonyOS 平台识别
- config.sub 需添加 linux-ohos* kernel-os 组合支持

### HMDFS Owner 不匹配（新发现）
- HMDFS 文件系统的 owner 与当前用户不匹配
- `umask 077 && mktemp -d` 创建的临时目录无法被当前用户访问
- 需修改 configure 移除 umask 077

### OpenSSL 配置路径
- CFLAGS 需设置 `-I$DEFAULT_PREFIX/include`

### c-ares 运行时依赖
- configure 检测到 c-ares，需安装 c-ares 预编译包

## 预编译包下载

- pgbouncer-1.22.1-ohos-aarch64.tar.gz (6.5MB)
- pgbouncer-1.22.1-ohos-aarch64-debug.tar.gz (1.3MB)

## 安装验证

```bash
pgbouncer --version
# 输出: PgBouncer 1.22.1
#       libevent 2.1.12-stable
#       adns: c-ares 1.34.6
#       tls: OpenSSL 3.0.13 30 Jan 2024
```