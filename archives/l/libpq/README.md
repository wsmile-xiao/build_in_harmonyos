# libpq

PostgreSQL客户端库，提供连接PostgreSQL数据库的C语言API。

## 软件简介

libpq是PostgreSQL的前端库，包含：
- 数据库连接API（PQconnectdb、PQsetdbLogin等）
- 查询执行API（PQexec、PQprepare等）
- 结果处理API（PQresultStatus、PQgetvalue等）
- 异步连接和查询支持
- SSL/TLS加密连接支持

## 安装指南

使用预编译包安装：
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libpq 16
```

## 版本信息

### 16 (推荐版本)

**编译状态**：published ✅
**编译日期**：2026-05-27
**质量门禁**：G0-G4全部通过

**产物详情**：
- libpq.so.5.16 (动态库，321KB)
- libpq.a (静态库，243KB)
- 头文件、pkgconfig文件

**关键技术**：
- VPATH构建避免HMDFS权限问题
- sed修改configure umask设置
- 禁用ICU依赖

## 编译详情

详见 `16/notes.md`。

## 许可证

PostgreSQL许可证（类似BSD/MIT）。