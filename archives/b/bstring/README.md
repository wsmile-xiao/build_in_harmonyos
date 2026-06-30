# bstring

Fork of Paul Hsieh's Better String Library — 一个专注于安全性和易用性的 C 语言字符串处理库。

## 基本信息

| 属性 | 值 |
|------|-----|
| License | BSD-3-Clause |
| 语言 | C |
| 构建系统 | meson |
| 当前版本 | 1.0.3 |
| 类型 | 共享库 |

## 安装产物

- **共享库**: `libbstring.so.1.0.3`（含符号链接 libbstring.so → libbstring.so.1 → libbstring.so.1.0.3）
- **头文件**: `bstraux.h`, `bstrlib.h`
- **pkg-config**: `bstring.pc`

## 核心功能

bstring 提供以下核心 API：
- `bfromcstr()` — 从 C 字符串创建 bstring
- `bdata()` — 获取 bstring 的 C 字符串数据
- `blength()` — 获取 bstring 长度
- `bstrcpy()` — 复制 bstring
- `bstrcmp()` — 比较 bstring
- `bstr2cstr()` — 将 bstring 转换为 C 字符串
- `bdestroy()` — 销毁 bstring 释放内存

## HarmonyOS 平台注意事项

1. 构建时必须使用 CC wrapper 自动签名 ELF 二进制（meson sanity check 要求）
2. 必须使用 GNU ld (`-fuse-ld=/data/service/hnp/bin/ld.bfd`) 替代平台 lld
3. 验证方式为 pkg-config 检查 + 实际 C 程序链接运行，无命令行工具