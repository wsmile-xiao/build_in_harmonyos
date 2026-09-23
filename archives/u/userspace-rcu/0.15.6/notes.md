# userspace-rcu 0.15.6 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-27
- 编译器: clang/clang++ (15.0.4)
- 状态: published

## 编译步骤

1. 下载源码并解压
2. 应用补丁: 0001-fix-tmpdir-for-hmdfs.patch (修复 HMDFS 临时目录权限问题)
3. 更新 config.guess/config.sub 以识别 OHOS 平台
4. 在 source() 中修复 umask 077→002 (E011: configure 生成的临时脚本权限)
5. Out-of-tree 构建: mkdir build && cd build && ../configure --prefix=... && make -j$(nproc)
6. make install DESTDIR=$TEST_PREFIX
7. make check (tests/unit)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别平台 | 旧版 config.guess (2022-01-09) 不支持 OHOS | 从 babeltrace2 归档复制更新的 config.guess/config.sub |
| 2 | configure 临时目录创建失败 | HMDFS 文件系统 umask 077 创建目录权限过严 | 补丁修改 umask 077→002, 使用 .config-tmp 子目录 |
| 3 | In-tree build 失败 | HMDFS 上 configure 生成的临时文件权限问题 | 使用 out-of-tree 构建 + 补丁修复 |

## 源码修改

### patches/0001-fix-tmpdir-for-hmdfs.patch
- 修改 configure 中的临时目录创建逻辑:
  - umask 077 → umask 002 (放宽权限)
  - ./confXXXXXX → ./.config-tmp/confXXXXXX (使用子目录)
  - mkdir → mkdir -p (确保父目录存在)

### source() 中的内联修复
- umask 077 → umask 002 (与 babeltrace2 相同的 E011 修复模式)
- config.guess/config.sub 更新 (从系统或 conan 缓存复制支持 OHOS 的版本)

## 依赖版本

无外部依赖 (standalone library)

## 验证结果

```
make check 结果:
# TOTAL: 636
# PASS:  632
# SKIP:  4
# FAIL:  0
# ERROR: 0

跳过的测试为 Linux 特定的 sysfs 测试，不影响 OHOS 平台使用。
```

## 产物

| 文件 | 说明 |
|------|------|
| lib/liburcu.a/.so | RCU base library |
| lib/liburcu-bp.a/.so | Bulletproof RCU |
| lib/liburcu-cds.a/.so | Concurrent Data Structures |
| lib/liburcu-common.a/.so | Common utilities |
| lib/liburcu-mb.a/.so | Memory barrier RCU |
| lib/liburcu-memb.a/.so | Memory barrier with explicit migration |
| lib/liburcu-qsbr.a/.so | Quiescent State Based Reclamation |
| include/urcu/*.h | RCU API 头文件 |

## 注意事项

- HMDFS 文件系统对 autotools 临时目录创建有特殊限制
- 建议所有 autotools 软件包使用 out-of-tree 构建
- config.guess 需要更新以识别 OHOS (aarch64-unknown-linux-ohos) 平台
---

**编译结束**: 2026-08-27 12:12
**最终状态**: built
