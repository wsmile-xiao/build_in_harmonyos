# avro-c 1.12.0 — OpenHarmony 编译记录

## 基本信息
- 软件: avro-c (Apache Avro C 库)
- 版本: 1.12.0
- 构建系统: CMake
- 目标: ohos-aarch64

## 简介
Apache Avro 是一个数据序列化系统，avro-c 是其 C 语言实现。提供：
- 数据序列化/反序列化
- Schema 解析和验证
- 二进制和 JSON 编码
- RPC 支持
- 多种压缩 Codec 支持

## 编译指导

### 必需依赖
- jansson >= 2.7 (JSON 库)

### 可选依赖（已启用）
- zlib (deflate codec)
- snappy (snappy codec)
- liblzma (lzma codec)

### 源码结构
使用完整 Apache Avro tarball，保留 share 目录：
```
├── avro-c-1.12.0.orig/  (lang/c 内容)
└── share/               (测试数据)
    └── test/data/schemas/
```

### 编译命令
```bash
mkdir build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=$HOME/usr/local -DCMAKE_BUILD_TYPE=Release -DCMAKE_EXE_LINKER_FLAGS="-lc++"
make -j$(nproc)
make install
```

## 补丁清单

| 补丁 | 说明 |
|------|------|
| 0001-version.sh.patch | bash 路径修复 |
| 0002-src-CMakeLists.txt.patch | SOVERSION 空值处理 |

## 已知限制

1. OpenHarmony bash 位于 `/data/service/hnp/bin/bash`，需使用 `#!/usr/bin/env bash`
2. CMake 可能无法正确获取 SOVERSION，需手动设置
3. snappy 是 C++ 库，需添加 `-lc++` 链接参数

## 功能验证

```bash
# 库文件
ls ~/usr/local/lib/libavro*
# 输出: libavro.a  libavro.so

# 工具
~/usr/local/bin/avrocat --help
```

## 测试结果

- 通过: 26/26 (100%)