# xnvme 0.7.5 — OpenHarmony 预编译包

## 概述

xnvme 是一个跨平台的 NVMe 库和工具集，提供对 NVMe 设备的用户空间访问。

本包为 OpenHarmony (aarch64) 平台预编译版本。

## 版本信息

| 项目 | 值 |
|------|-----|
| 软件 | xnvme |
| 版本 | 0.7.5 |
| 平台 | OpenHarmony (aarch64) |
| 构建系统 | meson + ninja |
| 编译器 | clang 15.0.4 |
| 编译日期 | 2026-06-25 |
| 状态 | published |

## 包内容

```
xnvme-0.7.5-ohos-aarch64.tar.gz
├── bin/          # xnvme 工具和测试程序
│   ├── xnvme
│   ├── xnvme_file
│   ├── xnvme-driver
│   ├── lblk
│   ├── kvs
│   ├── xdd
│   ├── zoned
│   └── xnvme_tests_* / xnvme_* (examples)
├── lib/          # 共享库和静态库
│   ├── libxnvme.so.0.7.5
│   ├── libxnvme.so.0 -> libxnvme.so.0.7.5
│   ├── libxnvme.so -> libxnvme.so.0
│   └── libxnvme.a
├── include/      # 头文件
│   └── libxnvme*.h
├── share/man/    # man 手册页
│   └── man1/
└── lib/pkgconfig/
    └── xnvme.pc
```

## 安装方法

```bash
# 解压到目标前缀
tar xzf xnvme-0.7.5-ohos-aarch64.tar.gz -C /
```

## 已启用的后端

| 后端 | 状态 | 说明 |
|------|------|------|
| linux | ✅ 已启用 | Linux NVMe ioctl 后端 |
| ramdisk | ✅ 已启用 | 内存盘后端（用于测试） |
| spdk | ❌ 已禁用 | 需要网络下载子项目 |
| fbsd | ❌ 已禁用 | FreeBSD 后端 |
| macos | ❌ 已禁用 | macOS 后端 |
| windows | ❌ 已禁用 | Windows 后端 |
| vfio | ❌ 已禁用 | VFIO 后端 |

## 已禁用的可选依赖

| 依赖 | 原因 |
|------|------|
| spdk | 子项目需网络下载，无预编译包 |
| liburing | 不可用 |
| libvfn | 不可用 |
| libisal | 不可用 |
| libaio | 不可用 |
| cbi_async_posix | musl libc 缺少 POSIX AIO 函数 |

## 源码修改

补丁文件: `patches/0001-meson.build.patch` (+6/-3 行)

1. 在 meson.build 的 `system_support` 列表中添加 `'harmonyos'`
2. 添加 `is_linux = is_linux or is_harmonyos` 将 OpenHarmony 映射为 Linux
3. 修复 `error()` 中使用未定义变量 `exec_env` 的问题

## 测试结果

- 编译: 143/143 目标完成
- 测试: 32/52 通过（20 个失败因缺少真实 NVMe 硬件设备）
- 功能验证: xnvme library-info 正常，版本 0.7.5，Linux 后端已启用

## 相关文件

- `manifest.yaml` — 版本清单
- `notes.md` — 适配笔记
- `reports/test-report.md` — 详细测试报告
- `reports/quality-report.md` — 质量门禁报告
- `patches/0001-meson.build.patch` — 源码补丁
