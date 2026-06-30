# libesedb

用于访问可扩展存储引擎 (ESE) 数据库文件 (EDB) 格式的库。

## 简介

libesedb 是一个 C 库，提供对 Windows 可扩展存储引擎 (Extensible Storage Engine, ESE) 数据库文件格式的读写访问。ESE 数据库也称为 JET Blue 数据库，被广泛用于 Windows 系统中的多种应用数据存储，包括 Active Directory、Exchange Server、Windows Search、SRUM (System Resource Usage Monitor) 等。

该项目还包含两个终端工具：
- **esedbexport**: 导出 ESE 数据库表内容为 CSV/JSON 等格式
- **esedbinfo**: 显示 ESE 数据库文件信息

## 官网

https://github.com/libyal/libesedb

## 许可证

LGPL-3.0-or-later

## 编译信息

| 版本 | 状态 | 编译日期 | 构建系统 | 补丁数 |
|------|------|----------|----------|--------|
| 20240420 | built | 2026-06-26 | autotools | 6 |

### 补丁说明

| 补丁文件 | 说明 |
|----------|------|
| 0001-common-config.h.patch | 配置头文件平台适配 |
| 0002-config.guess.patch | E007: 添加 HarmonyOS 系统检测分支 |
| 0003-config.sub.patch | E007: 添加 ohos-linux/ohos* OS 模式支持 |
| 0004-configure.patch | E011: umask 077→022 修复 HMDFS 权限问题 |
| 0005-dpkg-changelog.patch | Debian changelog 版本号修正 |
| 0006-libesedb.spec.patch | RPM spec 版本号修正 |

### 已知平台问题

| 问题编号 | 说明 | 解决方案 |
|----------|------|----------|
| E007 | GNU config.guess 不识别 HarmonyOS | 内联修改 config.guess/config.sub |
| E011 | HMDFS umask 077 导致 config.status 权限拒绝 | 替换 umask 077→022 |
| E053 | bindtextdomain 在独立 libintl 中 | 链接 -lintl (gettext 0.26) |

## 依赖

无外部依赖。内部包含 libyal 系列子库（libcerror, libcdata, libclocale 等）。
