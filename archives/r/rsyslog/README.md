# rsyslog

Rsyslog是一个高性能的日志系统
支持日志收集、处理和转发。

## 基本信息

- **版本**: 8.2404.0
- **构建系统**: autotools
- **编译日期**: 2026-05-28
- **状态**: built

## 简介

Rsyslog提供企业级的日志管理解决方案
支持多种输入输出模块和日志处理功能。

## 已编译版本

| 版本 | 状态 | 预编译包 | 补丁数 |
|------|------|----------|--------|
| 8.2404.0 | built | ❌ | 9 |

## OHOS 适配要点

### HMDFS 权限问题
- configure/config.status 临时文件创建失败
- 解决方案：修改使用 $TMPDIR 绝对路径

### pthread_cancel 问题
- OHOS/musl 不支持 pthread_cancel
- 解决方案：添加条件编译使用替代方案

## 功能验证

```bash
rsyslogd -v
# 输出: rsyslogd 8.2404.0
```

## 参考

- 官网: https://www.rsyslog.com/