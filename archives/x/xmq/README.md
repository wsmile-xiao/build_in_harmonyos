# XMQ

## 软件描述

XMQ (eXtended Markup Query) 是一个配置语言和数据存储语言，兼容 XML/HTML 和 JSON。它提供了更简洁的语法来处理结构化数据，支持查询、转换和验证操作。

## 功能特性

- 简洁的配置语言语法
- 兼容 XML/HTML 和 JSON
- 数据查询和转换
- Schema 验证
- XSLT 转换支持
- 多种输入/输出格式

## 官网

- 官方网站: https://libxmq.org
- GitHub 仓库: https://github.com/libxmq/xmq

## 编译状态

### 版本 4.2.0

**状态**: partial (编译成功，但存在系统限制问题)

**编译日期**: 2026-06-17

**编译环境**: HarmonyOS (aarch64-unknown-linux-ohos)

**遇到的问题**:
1. E007: config.guess 无法识别 HarmonyOS 平台
2. TMPDIR 权限问题导致 config.status 临时文件创建失败
3. 动态库依赖需要设置 LD_LIBRARY_PATH
4. 安全弹窗验证失败（可能需要 ELF 签名）

**解决方案**:
1. 使用 `patch-autotools-ohos.pl` 补丁修复 config.guess/config.sub
2. 手动创建配置文件绕过 config.status 的限制
3. 手动创建静态库和动态库
4. 成功生成 xmq 可执行文件

**依赖**:
- zlib
- libxml2
- libxslt
- libgcrypt (可选)
- libgpg-error (可选)

## 使用方法

```bash
# 查看 XML 文件
xmq view file.xml

# 转换 XML 到 JSON
xmq convert --to-json file.xml > file.json

# 查询数据
xmq query '//element[@attr="value"]' file.xml

# 验证 Schema
xmq validate --schema schema.xmq file.xml
```

## 注意事项

在 HarmonyOS 上运行时，需要设置 LD_LIBRARY_PATH：

```bash
export LD_LIBRARY_PATH=$HOME/usr/local/lib:$LD_LIBRARY_PATH
xmq --version
```