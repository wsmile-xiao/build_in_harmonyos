# ifstat — 网络接口带宽统计工具

## 简介

ifstat 是一个轻量级的网络接口带宽统计工具，用于实时监控 Linux/Unix 系统中各网络接口的入/出流量。它通过读取 `/proc/net/dev` 获取统计数据，以 KB/s 为单位周期性地报告各接口的带宽使用情况。

## 已编译版本

- **版本**: 1.1
- **状态**: published
- **许可证**: GPL-2.0-or-later
- **构建系统**: autotools

## 下载地址

- 源码: https://deb.debian.org/debian/pool/main/i/ifstat/ifstat_1.1.orig.tar.gz

## 用法示例

```bash
# 显示版本
ifstat -v

# 单次采样（1秒间隔，1次）
ifstat 1 1

# 指定接口统计
ifstat -i wlan0 1 1

# 列出所有接口
ifstat -l

# 显示帮助
ifstat -h
```

## 注意事项

- ifstat 使用 `-v` 显示版本号，不支持 `--version`
- 需要读取 `/proc/net/dev`，运行需要适当的权限
- 编译内嵌驱动为 proc（读取 /proc/net/dev），不支持 SNMP 驱动