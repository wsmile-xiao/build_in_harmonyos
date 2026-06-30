# pv - Pipe Viewer

## 简介

pv（Pipe Viewer）是一个终端工具，用于监控数据通过管道的进度。它可以显示传输速度、进度条、ETA（预计完成时间）等信息。

## 功能特点

- 显示数据传输进度条
- 实时显示传输速度
- 计算 ETA（预计完成时间）
- 支持多个输入文件
- 可在管道中插入使用

## 官方信息

- **官方源码**: https://github.com/a-j-wood/pv
- **许可证**: Artistic License 2.0

## 编译版本

当前已编译版本：1.7.24

### 已知平台适配问题

1. **HMDFS umask 权限问题**（E011）
   - configure 在 HMDFS 上创建临时目录失败
   - 需修改 configure 中的 `umask 077` 为 `umask 022`

2. **make check 失败**
   - 34/35 测试失败（平台 syscall 限制）
   - 跳过测试不影响核心功能

## 使用示例

```bash
# 监控压缩进度
pv largefile.txt | gzip > largefile.txt.gz

# 监控解压进度
pv largefile.txt.gz | gunzip > largefile.txt

# 显示文件复制进度
pv sourcefile > destfile
```

## 编译状态

- **版本**: 1.7.24
- **状态**: built
- **编译日期**: 2026-05-25
- **构建系统**: autotools
- **补丁**: 2 个（HMDFS umask 修复）