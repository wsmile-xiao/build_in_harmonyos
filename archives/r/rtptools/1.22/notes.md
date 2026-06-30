# rtptools 1.22 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-25
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. `autoreconf -fi` — 生成 configure 脚本（源码包未预生成）
2. `./configure --prefix=$DEFAULT_PREFIX` — 配置
3. `make -j1` — 编译（4 个二进制：rtpdump, rtpplay, rtpsend, rtptrans）
4. `make install DESTDIR=$TEST_PREFIX` — staging 安装
5. `make check` — 无测试目标
6. `make install` — 安装到 $DEFAULT_PREFIX
7. `ohc-run.py package` — 打包预编译包

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 下载 URL 404 | 任务提供的 b4kn0/rtptools URL 不存在 | 搜索发现正确仓库为 irtlab/rtptools，tag 为 1.22（不带 v 前缀） |
| 2 | configure 需 autoreconf | GitHub archive tarball 不含预生成 configure | 运行 `autoreconf -fi` 生成 configure 脚本 |
| 3 | config.status 权限拒绝 | `umask 077` + mktemp -d 创建的目录权限为 0700，但 HarmonyOS 平台文件归属 uid 与进程 uid 不同，导致进程无法写入自己创建的临时目录 | 移除 configure 和 config.status 中的 `umask 077`，让 mktemp 使用默认 umask 创建目录 |
| 4 | manifest 缺少 build_system | G4 检查文本搜索 `build_system:` 字段 | 在 manifest.yaml 的 build 段添加 `build_system: autotools` |

## 源码修改

- **0001-config.status.patch**: 移除 config.status 中的 `umask 077` 调用，修复 HarmonyOS 平台临时目录权限问题
- **0002-configure.patch**: 移除 configure 中的 `umask 077` 调用，同上

## 依赖版本

无外部依赖。仅需要标准 C 库和系统头文件。

## 验证结果

```bash
$ rtpdump -h
usage: rtpdump [-F hex|ascii|rtcp|short|payload|dump|header] [-f infile] [-o outfile] [-t minutes] [-x bytes] [address]/port > file

$ file rtpdump
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
```

所有 4 个二进制（rtpdump, rtpplay, rtpsend, rtptrans）编译并安装成功。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| rtptools-1.22-ohos-aarch64.tar.gz | 351KB | 预编译包（ELF 已签名） |
| rtptools-1.22-ohos-aarch64-debug.tar.gz | - | 调试符号包 |

## 注意事项

- GitHub 仓库为 `irtlab/rtptools`（非 `b4kn0/rtptools`），tag 为 `1.22`（不带 v 前缀）
- 源码包为 GitHub archive tarball，不含预生成 configure 脚本，需要 autoreconf
- `umask 077` 是 autoconf 标准实践，但在 HarmonyOS 平台导致权限问题，需移除
- 编译有少量 warning（format string, unused variable, pointer sign），不影响功能
---

**编译结束**: 2026-06-25 16:55
**最终状态**: built
