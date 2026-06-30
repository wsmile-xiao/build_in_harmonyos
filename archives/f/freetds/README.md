# FreeTDS

FreeTDS 是一个开源的 TDS (Tabular Data Stream) 协议实现库，用于连接 Microsoft SQL Server 和 Sybase 数据库。

## 主要功能

- **libtds**: 核心 TDS 协议实现库
- **db-lib**: Microsoft db-lib API 实现
- **ct-lib**: Sybase ct-lib API 实现
- **ODBC 驱动**: 支持 ODBC 标准
- **实用工具**: tsql, freebcp, bsqldb, defncopy, datacopy

## 依赖

- 标准 C 库
- 可选: OpenSSL (用于加密连接)
- 可选: UnixODBC (用于 ODBC 支持)

## 鸿蒙适配

### 已解决的平台问题

| 问题编号 | 说明 | 解决方案 |
|---------|------|---------|
| E007 | config.guess 不识别 HarmonyOS | 添加 `*:HarmonyOS:*:*` case 分支 |
| E011 | HMDFS umask 权限问题 | 修改 `umask 077` → `022` |
| E091 | sockaddr_storage 重定义冲突 | `__OHOS__` 宏守卫 |

### 编译版本

- **1.4.23** (2026-05-20) - published

## 下载

预编译包可通过 cmd-pkgs 仓库获取：
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- freetds 1.4.23
```