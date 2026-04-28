# xxHash

## 简介
极快的非加密哈希算法库，包含 XXH32、XXH64、XXH3、XXH128 等算法。XXH3 在 ARM64 上可达 ~15GB/s 吞吐量，接近 RAM 带宽极限。

## OHOS 适配
- CMake 构建，源码与 HarmonyOS 完全兼容，无需补丁
- 49,948 个 sanity 测试全部通过
- 支持动态链接和静态链接

## 排除与替代
- xxhsum 可替代 md5sum/sha256sum 用于非加密哈希场景

## 依赖
- 标准 C 库

## 功能验证
```bash
xxhsum --version
xxhsum file.txt
xxhsum -H3 file.txt
```

## 参考
- 源码: https://github.com/Cyan4973/xxHash
