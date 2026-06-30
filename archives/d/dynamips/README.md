# dynamips — OpenHarmony aarch64 适配

dynamips 是一款 Cisco 路由器模拟器，用于模拟 Cisco 7200/3600/2691/3725/3745/2600/1700 等系列路由器，广泛应用于 GNS3 网络模拟平台。

## 适配版本

| 版本 | 状态 | 构建系统 | 说明 |
|------|------|----------|------|
| 0.2.23 | published | cmake | nojit模式，aarch64不支持JIT |

## 编译要点

- aarch64 平台必须使用 `DYNAMIPS_ARCH=nojit`（无 JIT 重编译支持）
- CMake 4.x 需添加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 解决兼容性
- 需 `-DANY_COMPILER=1` 跳过 gcc/clang 编译器白名单检查
- 依赖 standalone libelf 0.8.13（非 elfutils）

## 依赖项

- libelf 0.8.13 (standalone)
- libpcap 1.10.6 (预装)
- argp-standalone 1.5.0
- musl-fts 1.2.7
- musl-obstack 1.2.3
