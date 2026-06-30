# dynamips 0.2.23 — OpenHarmony aarch64 编译归档

## 软件简介

dynamips 是一款 Cisco 路由器模拟器（Cisco Router Simulation Platform），用于模拟 Cisco 7200/3600/2691/3725/3745/2600/1700 等系列路由器。它广泛应用于网络仿真和 GNS3 网络模拟平台中。

本项目为 dynamips 0.2.23 在 OpenHarmony (HarmonyOS) aarch64 平台上的编译适配版本。

## 编译信息

| 项目 | 值 |
|------|-----|
| 版本 | 0.2.23 |
| 构建系统 | cmake |
| 编译器 | clang 15.0.4 (aarch64-unknown-linux-ohos) |
| CMake 版本 | 4.1.2 |
| 构建模式 | nojit（aarch64 无 JIT 支持） |
| 编译日期 | 2026-06-17 |
| 状态 | published |

## 编译配置

```bash
cmake .. \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DDYNAMIPS_ARCH=nojit \
  -DANY_COMPILER=1 \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -DCMAKE_C_COMPILER=clang \
  -DCMAKE_PREFIX_PATH=$DEFAULT_PREFIX
```

## 依赖项

| 依赖 | 版本 | 来源 |
|------|------|------|
| libelf | 0.8.13 (standalone) | 手动编译安装 |
| libpcap | 1.10.6 | 预装 |
| argp-standalone | 1.5.0 | 预编译包 |
| musl-fts | 1.2.7 | 预编译包 |
| musl-obstack | 1.2.3 | 预编译包 |

## 交付物

预编译包产物：

| 文件 | 大小 | 说明 |
|------|------|------|
| `dynamips-0.2.23-ohos-aarch64.tar.gz` | 1.2MB | 主包（含 bin/lib/share，已 strip+签名） |
| `dynamips-0.2.23-ohos-aarch64-debug.tar.gz` | 246KB | 调试符号包 |

主包内容：
- `bin/dynamips` — Cisco 路由器模拟器主程序
- `bin/nvram_export` — NVRAM 配置导出工具
- `lib/external/libelf.so.0` — 外部依赖库
- `share/doc/` — 文档和手册页

## 使用方式

### 模拟器基本用法

```bash
# 查看版本
dynamips --version

# 启动 hypervisor 模式（用于 GNS3 集成）
dynamips -H 7200

# 模拟 Cisco 7200 路由器
dynamips -P 7200 <ios_image.bin>
```

### NVRAM 导出

```bash
# 从 NVRAM 文件导出启动配置
nvram_export nvram_file config_file [private_file]
```

## 重要说明

1. **nojit 模式**: aarch64 平台不支持 JIT 重编译器，所有模拟器均以 nojit 模式运行，性能较 x86 JIT 模式有所降低。
2. **libpcap 绝对路径**: 预编译包中 libpcap.so 使用绝对路径引用，部署时需确保路径一致或设置 `LD_LIBRARY_PATH`。
3. **ELF 签名**: 所有二进制已添加鸿蒙 `.codesign` 签名段，可在 HarmonyOS 系统上正常执行。
