# ossp-uuid

**OSSP UUID — 通用唯一标识符 (UUID/GUID) 生成库**

## Overview
ossp-uuid 是一个用于生成和解析 UUID（通用唯一标识符）的 C 库，支持 RFC 4122 定义的所有 UUID 版本：

- **UUID v1**: 基于时间和节点（MAC 地址）
- **UUID v3**: 基于名称的 MD5 哈希
- **UUID v4**: 基于随机数据
- **UUID v5**: 基于名称的 SHA-1 哈希

## Features
- 生成所有 RFC 4122 UUID 版本 (v1/v3/v4/v5)
- UUID 字符串编解码 (36 字节标准格式)
- 二进制 UUID 处理 (16 字节)
- 命令行工具 `uuid` 用于快速生成
- `uuid-config` 配置脚本用于编译链接
- pkg-config 支持 (uuid.pc)

## Usage
```bash
# 生成随机 UUID
uuid

# 生成基于名称的 UUID (MD5)
uuid -v3 ns:DNS example.com

# 解析 UUID
uuid -d 550e8400-e29b-41d4-a716-446655440000
```

## Build Method
ossp-uuid 使用 autotools 构建系统：
```bash
./configure --prefix=$PREFIX
make
make install
```

## Version History
- **1.6.2** (2026-07-03): 适配 OpenHarmony 平台

## Author
Ralf S. Engelschall (OSSP)

## License
MIT License

## Homepage
https://www.ossp.org/pkg/lib/uuid/

## OpenHarmony Compatibility
ossp-uuid 1.6.2 已在 OpenHarmony 鸿蒙内核 (aarch64) 上成功编译和测试。

### Build Notes
- 系统同名库 (libuuid) 强制静态链接 (R26)，避免污染 /lib
- config.guess/config.sub 替换为 automake 1.16 版本以支持 OHOS 平台检测 (E007)
- mktemp -d 在 HMDFS 上受 MAC 限制，改用 mkdir (E125)
- conan-verify 8 道门禁全部通过
