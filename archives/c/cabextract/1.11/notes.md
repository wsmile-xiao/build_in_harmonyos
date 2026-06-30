# cabextract 1.11 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-28
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

1. 源码下载: cabextract-1.11.tar.gz (489KB)
2. 手动解压到 tmp/cabextract-build (因 builds 目录权限问题)
3. 修改 config.guess: 添加 `aarch64:HarmonyOS:*:*)` 分支
4. 修改 config.sub: 在多处添加 `ohos*` 支持
5. 手动创建 Makefile 和 config.h (因 configure 无法写入临时文件)
6. 直接编译: `make -j1`
7. 安装: `make install` → ~/usr/local/bin/cabextract

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | E007/E072: 平台识别缺失 | 手动添加 `aarch64:HarmonyOS:*:*)` 和 `ohos*` 支持 |
| 2 | configure 无法写入临时文件 | HMDFS 权限限制 | 手动创建 Makefile 和 config.h，直接编译 |
| 3 | cabinfo.c 有独立的 main | 误编译多个 main 函数 | 排除 cabinfo.c，只编译 cabextract |

## 源码修改

- **0001-config.guess.patch**: 添加 HarmonyOS 平台识别
  - 在 `aarch64:Linux:*:*)` 前插入 `aarch64:HarmonyOS:*:*)` 分支
  - 输出三元组: `aarch64-unknown-linux-ohos`

- **0002-config.sub.patch**: 添加 ohos 操作系统支持
  - maybe_os 行: 添加 `linux-ohos* | ohos*`
  - OS 白名单: 添加 `ohos*`
  - kernel-os 白名单: 添加 `linux-ohos* | ohos*`

## 依赖版本

- clang 15.0.4 (系统自带)
- make 4.4.1 (GNU)
- 无外部库依赖

## 验证结果

```bash
$ ~/usr/local/bin/cabextract --version
cabextract version 1.11
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| cabextract | 96KB | 主程序二进制 |

## 注意事项

1. **平台适配**: 此版本在 HarmonyOS 上需要修改 config.guess 和 config.sub
2. **手动编译**: 因 configure 无法在当前目录创建临时文件，需手动生成 Makefile
3. **G0 门禁**: 由于手动绕过 configure，G0 干净构建验证失败（需后续修复）
---
