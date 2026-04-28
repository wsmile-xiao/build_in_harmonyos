# libaec — OpenHarmony 预编译包

## 软件简介
libaec 是自适应熵编码库，实现了 Golomb-Rice 算法，主要用于科学数据压缩。
提供 libaec 库和 SZ 兼容库（libsz）。

## 快速安装

```bash
# 下载预编译包后解压安装
tar xzf libaec-1.1.6-ohos-aarch64.tar.gz
cd libaec-1.1.6-ohos-aarch64
sh install-libaec-1.1.6.sh
```

或使用软件级安装脚本：
```bash
sh install.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 | 构建系统 |
|------|------|--------|----------|
| 1.1.6 | ✅ success | 0 | CMake |

## 库文件

安装后可用的库：
- `libaec.so` / `libaec.a` - 主库
- `libsz.so` / `libsz.a` - SZ 兼容库
- `libaec.h` / `szlib.h` - 头文件

## 使用示例

```c
#include <libaec.h>

// 编码
aec_stream strm;
strm.rsi = 128;
strm.flags = AEC_DATA_PREPROCESS | AEC_DATA_3BYTE;
// ... 配置并调用 aec_encode_init(), aec_encode(), aec_encode_end()

// 解码
// ... 配置并调用 aec_decode_init(), aec_decode(), aec_decode_end()
```

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- CMake 可用于项目集成