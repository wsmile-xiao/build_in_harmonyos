# Release Note — avro-c 1.12.0

**发布日期**: 2026-04-25 (最终版本)
**平台**: OpenHarmony aarch64

## 版本信息

- **软件**: avro-c
- **版本**: 1.12.0
- **上游源**: https://github.com/apache/avro

## 变更说明

- 首次为 OpenHarmony 平台编译 Apache Avro C 库
- 修复 OpenHarmony 平台兼容性问题
- **已启用全部压缩 Codec**: deflate, snappy, lzma
- **测试全部通过**: 26/26 (100%)

## 补丁列表（简化版）

| 补丁文件 | 说明 |
|---------|------|
| 0001-version.sh.patch | 修复 bash 路径 (#!/usr/bin/env bash) |
| 0002-src-CMakeLists.txt.patch | 处理空 SOVERSION |

**改进说明**: 使用完整 Apache Avro tarball 解压，保留 share 目录，无需修改测试路径。

## Codec 支持

| Codec | 状态 | 依赖 |
|-------|------|------|
| deflate | ✅ | zlib 1.3.1 |
| snappy | ✅ | snappy 1.1.10 |
| lzma | ✅ | liblzma 5.6.2 |

## 安装依赖

必需依赖：
- jansson 2.14 (JSON 库)

可选依赖（已安装）：
- zlib 1.3.1 (deflate codec)
- snappy 1.1.10 (snappy codec)
- liblzma 5.6.2 (lzma codec)

## 安装方法

```bash
sh install-avro-c-1.12.0.sh [prefix]
# 默认安装到 $HOME/usr/local
```

## 验证

```bash
# 检查库文件
ls ~/usr/local/lib/libavro*

# 检查工具
~/usr/local/bin/avrocat <avro-file>

# 检查 codec 支持
nm ~/usr/local/lib/libavro.a | grep codec
```

## 测试状态

- **通过: 26/26 (100%)**
- 质量门禁: G1-G4 全部 PASS

## 已知问题

无