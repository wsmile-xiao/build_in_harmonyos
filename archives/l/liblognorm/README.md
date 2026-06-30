# liblognorm

## 软件简介

liblognorm 是一个日志规范化库，用于解析和规范化日志消息。它是 rsyslog 项目的核心依赖库之一。

**主要功能**：
- 日志解析与规范化
- 支持基于规则的日志匹配
- 高性能日志处理

**项目地址**：https://www.liblognorm.com/

## 编译版本

- **当前版本**：2.0.6
- **编译状态**：published
- **编译日期**：2026-06-02

## 依赖关系

liblognorm 依赖以下库：

| 依赖库 | 版本 | 状态 |
|--------|------|------|
| libestr | 0.1.11 | ✅ 已编译 |
| libfastjson | 0.99.9 | ✅ 已编译 |

## 构建信息

- **构建系统**：autotools
- **配置选项**：`--prefix=/storage/Users/currentUser/usr/local`
- **编译器**：clang / clang++
- **补丁**：0001-configure.patch（umask 修复，生成 configure 脚本）

## 版本历史

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|----------|------|
| 2.0.6 | published | 2026-06-02 | 当前版本 |

## 使用说明

### 安装预编译包

```bash
# 通过 cmd-pkgs 安装
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- liblognorm 2.0.6
```

### 验证安装

```bash
# 检查库文件
ls ~/usr/local/lib/liblognorm.*

# 检查头文件
ls ~/usr/local/include/liblognorm.h
```

## 编译注意事项

1. **源码包特性**：源码包未包含预生成的 `configure` 脚本，需要运行 `autoreconf -fi` 生成
2. **补丁说明**：`0001-configure.patch` 包含生成的 configure 脚本，确保在鸿蒙平台上正确构建
3. **依赖顺序**：需要先编译安装 `libestr` 和 `libfastjson`

## 知识沉淀

- liblognorm 依赖 libestr 和 libfastjson 库
- 源码包未包含预生成的 configure，需要 autoreconf
- libestr 和 libfastjson 均已提供预编译包

## 参考链接

- 官方文档：https://www.liblognorm.com/documentation/
- 源码仓库：https://github.com/rsyslog/liblognorm