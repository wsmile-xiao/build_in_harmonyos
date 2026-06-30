# unixODBC

 unixODBC 是一套开放源代码的 ODBC（Open Database Connectivity）驱动管理器，提供统一的数据库访问接口。

## 基本信息

- **版本**: 2.3.12
- **构建系统**: autotools
- **编译日期**: 2026-05-27
- **状态**: built

## 简介

 unixODBC 提供了 ODBC 驱动管理器、驱动配置工具和测试工具，支持多种数据库系统的统一访问。

## 已编译版本

| 版本 | 状态 | 预编译包 | 补丁数 |
|------|------|----------|--------|
| 2.3.12 | built | ❌ | 6 |

## OHOS 适配要点

### HMDFS 文件系统权限问题
- configure/config.status 在HMDFS上创建临时文件失败
- 需手动生成libltdl/Makefile和config.h

### lt__argz 函数缺失
- libltdl需要编译lt__argz.c
- 需正确的LTDL和LT_CONFIG_H宏定义

## 依赖

无外部依赖

## 功能验证

```bash
isql --version
# 输出: unixODBC 2.3.12
```

## 参考

- 官网: https://www.unixodbc.org/
- 源码: https://github.com/lurcher/unixODBC