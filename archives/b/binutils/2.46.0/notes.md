# binutils 2.46.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-25
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码（清华镜像）：https://mirrors.tuna.tsinghua.edu.cn/gnu/binutils/binutils-2.46.0.tar.gz
2. 修改 config.guess/config.sub 支持 HarmonyOS（使用 patch-autotools-ohos.pl）
3. 修改所有 configure 脚本中的 umask 077 为 umask 022（解决 HMDFS 权限问题）
4. 执行 configure：`./configure --prefix=/storage/Users/currentUser/usr/local --disable-gprofng`
5. 执行 make：`make -j2`
6. 执行 staging 安装：`make install DESTDIR=/storage/Users/currentUser/test-install-binutils-2.46.0`
7. 执行测试：`make check`（跳过部分测试，缺少 dejagnu）
8. 制作预编译包：`python3 scripts/ohc-run.py package binutils 2.46.0`
9. 本地安装：`make install`
10. 验证工具：`ld --version`、`as --version`等

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| E007 | config.guess 无法识别 HarmonyOS | GNU config.guess 缺少 HarmonyOS 检测分支 | 使用 patch-autotools-ohos.pl 补丁 |
| E011 | config.status 创建临时文件失败（Permission denied） | HMDFS UID 映射导致 umask 077 目录不可写 | 修改所有 configure 脚本 umask 077 → 022 |
| gprofng | gprofng 编译失败（SIGEV_THREAD_ID 未定义） | 使用 Linux 特定信号机制 | 禁用 gprofng（--disable-gprofng） |

## 源码修改

修改了 16 个文件，生成 16 个补丁：
- 0003-config.guess.patch: 添加 HarmonyOS 系统识别
- 0004-config.sub.patch: 添加 ohos-linux 三元组
- 0001-bfd-configure.patch ~ 0016-zlib-configure.patch: umask 077 → 022

## 依赖版本

无外部依赖（binutils 自包含）

## 验证结果

```bash
ld --version    # GNU ld (GNU Binutils) 2.46.0.20260210
as --version    # GNU assembler (GNU Binutils) 2.46.0.20260210
ar --version    # GNU ar (GNU Binutils) 2.46.0.20260210
nm --version    # GNU nm (GNU Binutils) 2.46.0.20260210
objdump --version  # GNU objdump (GNU Binutils) 2.46.0.20260210
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| binutils-2.46.0-ohos-aarch64.tar.gz | 87.8 MB | 预编译包（含调试符号） |
| binutils-2.46.0-ohos-aarch64-debug.tar.gz | 85.8 MB | 调试符号包 |

## 注意事项

- gprofng 在 HarmonyOS 上不可用，需禁用
- 所有 configure 脚本都需要修改 umask（共 16 个）
- 质量门禁 G0-G4 全部通过

---

**编译结束**: 2026-05-25 17:29
**最终状态**: built
