# nettle 4.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-04
- 编译器: clang/clang++
- 状态: built (conan-verified)

## 编译步骤

```bash
# 1. 下载源码
# Source: https://ftp.gnu.org/gnu/nettle/nettle-4.0.tar.gz

# 2. 应用补丁 (3个)
patch -p1 < patches/0001-config.guess.patch  # HarmonyOS aarch64 识别
patch -p1 < patches/0002-config.sub.patch    # ohos-linux 映射
patch -p1 < patches/0003-configure.patch     # umask 077→022 (hmdfs)

# 3. 配置 (conan create 自动处理)
# CC=clang CXX=clang++
# CPPFLAGS/LDFLAGS 包含 gmp 路径 (nettle 4.0 不再支持 --with-include-path)

# 4. 编译
make -j1

# 5. 测试
make check  # 117 tests all passed
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 不识别 HarmonyOS | E007 | 添加 HarmonyOS aarch64 检测分支 |
| 2 | configure umask 077 在 hmdfs 上失败 | E011 | 改为 umask 022 |
| 3 | --with-include-path 不被识别 | nettle 4.0 API 变更 | 改用 CPPFLAGS/LDFLAGS 传递 gmp 路径 |
| 4 | sha256_digest 参数数量变更 | nettle 4.0 API 变更 | 移除 length 参数 (2个参数) |

## 源码修改

- patches/0001-config.guess.patch: HarmonyOS aarch64 识别
- patches/0002-config.sub.patch: ohos-linux 映射
- patches/0003-configure.patch: umask 077→022

## 依赖版本

- gmp/6.3.0 (hogweed 公钥加密库依赖)

## 验证结果

- conan create: PASS (G0-G4 全部通过)
- W3 本地 CI 模拟: PASS
- test_package: SHA256('abc') + AES-128 block encryption PASS
- 上游 make check: 117/117 tests passed

## 注意事项

- nettle 4.0 的 sha256_digest API 从 3 参数变为 2 参数 (移除了 length)
- nettle 4.0 的 configure 不再支持 --with-include-path/--with-lib-path，需用标准 CPPFLAGS/LDFLAGS
- 生成 libnettle.a (加密库) 和 libhogweed.a (公钥加密库)

---

**编译结束**: 2026-09-04
**最终状态**: built (conan-verified: G0-G4 PASS, W3 PASS)
