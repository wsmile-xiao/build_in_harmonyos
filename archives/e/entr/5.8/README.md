# entr 5.8 — OpenHarmony 编译记录

## 基本信息
- **软件**: entr (Event Notify Test Runner)
- **版本**: 5.8
- **构建系统**: 自定义 configure 脚本
- **目标平台**: ohos-aarch64 (HarmonyOS)
- **编译日期**: 2026-05-15

## 功能简介

entr 是一个命令行工具，用于监控文件变化并执行指定命令。主要用途：
- 自动运行测试
- 自动编译代码
- 自动重启服务

## 编译指导

### 配置

```bash
# 必须设置 TARGET_OS=Linux（HarmonyOS 平台识别问题）
TARGET_OS=Linux ./configure
```

### 编译

```bash
make PREFIX=/usr/local
```

### 安装

```bash
# DESTDIR 模式（打包用）
make install PREFIX=/usr/local DESTDIR=/path/to/staging

# 本地安装
make install PREFIX=/usr/local
```

## 补丁清单

**无补丁** - 源码未经修改，通过环境变量实现平台适配。

## 已知限制

### 1. 平台识别问题
- **现象**: configure 脚本通过 `uname` 判断操作系统，HarmonyOS 返回 "HarmonyOS"
- **解决**: 设置 `TARGET_OS=Linux` 环境变量

### 2. 测试套件依赖
- **现象**: `make check` 需要 tmux 工具
- **解决**: 已执行手动功能测试验证核心功能

### 3. 临时目录限制
- **现象**: `/tmp` 目录只读
- **解决**: 使用 `$TMPDIR` 或 `$HOME/tmp`

## 功能验证

### 测试状态
- ✅ 版本显示正常
- ✅ 帮助信息正常
- ✅ 文件监控功能正常
- ✅ 非交互模式 (-n) 正常
- ✅ 执行后退出 (-z) 正常
- ✅ 错误处理正常

详见: `reports/test-report.md`

## 使用示例

```bash
# 监控 Python 文件变化
echo "main.py" | entr -n python main.py

# 监控 Go 项目
ls *.go | entr -n go test ./...

# 后台运行
echo "config.yaml" | entr -r service-restart.sh
```

## 参考链接

- 官方网站: https://eradman.com/entrproject/
- 源码下载: https://eradman.com/entrproject/code/entr-5.8.tar.gz