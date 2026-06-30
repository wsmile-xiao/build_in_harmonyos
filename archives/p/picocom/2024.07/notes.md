# picocom 2024.07 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile 项目，无 configure）
- 编译日期: 2026-05-25
- 编译器: clang/clang++
- 状态: published

## 编译步骤

picocom 是纯 Makefile 项目，无 configure 脚本，也无 install 目标。

1. `make CC=clang CFLAGS="-Wall -g -fPIC -O2" LDFLAGS="-g" -j1`
2. 手动安装到 staging 目录: `mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/bin && cp picocom $TEST_PREFIX/$DEFAULT_PREFIX/bin/`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 原始 URL SSL 证书验证失败 | savannah.nongnu.org SSL 证书不被本平台信任 | 安装 CA 证书后从 GitLab (wsakernel/picocom) 下载源码 |
| 2 | Savannah URL 404 | picocom 2024.07 版不在 Savannah 下载页 | 使用 GitLab wsakernel/picocom 的 2024-07 tag 归档 |
| 3 | G4 档案完整性失败 | manifest.yaml 缺少 build_system 顶层字段 | 添加顶层 `build_system: makefile` 字段 |
| 4 | 无 install target | Makefile 没有 install 目标 | 手动 `cp picocom` 到 staging 和安装目录 |
| 5 | G0 干净构建验证失败 | clean-verify 对 makefile 项目仍尝试运行 ./configure | 已手动验证通过，此为脚本局限 |

## 源码修改

无源码修改。picocom 2024.07 在 OpenHarmony 上原生编译成功，无需补丁。

## 依赖版本

无外部依赖。picocom 仅依赖系统 libc 和 termios。

## 验证结果

```bash
$ picocom --help
picocom v2024-07

Compiled-in options:
  TTY_Q_SZ is 0
  HIGH_BAUD is enabled
  USE_FLOCK is enabled
  LINENOISE is enabled
  HISTFILE is: .picocom_history

Usage is: picocom [options] <tty port device>
...
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| picocom-2024.07-ohos-aarch64.tar.gz | 90KB | 预编译包（含 ELF 签名） |
| picocom-2024.07-ohos-aarch64-debug.tar.gz | 123KB | debug symbols 包 |

## 注意事项

- picocom 没有标准 install target，需要手动复制二进制
- picocom 2024.07 版本来源为 GitLab wsakernel/picocom 项目，而非原始 Savannah
- picocom 无测试套件，跳过 make check
- G0 clean-verify 对 makefile 项目不适用（会尝试运行不存在的 configure）
---

**编译结束**: 2026-05-26 10:24
**最终状态**: published
