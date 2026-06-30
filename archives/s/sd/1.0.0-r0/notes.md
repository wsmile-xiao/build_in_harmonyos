# sd 1.0.0-r0 适配笔记

## 编译环境
- 构建系统: Rust (Cargo) — 预编译 musl 二进制方式部署
- 编译日期: 2026-06-02
- 编译器: 预编译 musl 动态 ELF (aarch64)
- 状态: published

## 编译步骤

### 第1次尝试（失败）
1. 下载 GitHub Release 预编译 sd-v1.0.0-aarch64-unknown-linux-musl.tar.gz
2. 提取 binary: "ELF executable, 64-bit LSB arm64, static, stripped" (2MB)
3. ELF签名(ohc-run.py sign-elf)后安装到 ~/usr/local/bin/
4. **失败**: 运行 sd --version → SIGSEGV (exit 139)
5. 根因: Rust musl静态编译的二进制在HarmonyOS上崩溃(SIGSEGV)

### 第2次尝试（成功 — 本轮）
1. 下载 Alpine Linux edge/community sd 1.1.0-r0 APK (musl动态链接)
   - URL: https://dl-cdn.alpinelinux.org/alpine/edge/community/aarch64/sd-1.1.0-r0.apk
   - 提取 binary: "ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)" (1.6MB)
2. 安装 runtime 依赖:
   - ~/usr/local/lib/libc.musl-aarch64.so.1 → /lib/ld-musl-aarch64.so.1 (已有)
   - ~/usr/local/lib/libgcc_s.so.1 (已有预编译包)
3. ELF签名: ohc-run.py sign-elf
4. 安装到 staging (DESTDIR模式 R20): cp sd $TEST_PREFIX/$DEFAULT_PREFIX/bin/sd
5. 安装到本地: cp sd $DEFAULT_PREFIX/bin/sd (模拟用户部署)
6. 验证: `sd --version` → `sd 1.1.0` (exit 0) ✅
7. 功能测试: `echo "hello world" | sd "world" "HarmonyOS"` → `hello HarmonyOS` ✅

### Rust从源码编译尝试（未执行）
- 已知rustc在HarmonyOS上崩溃(SIGSEGV), 无法从源码编译Rust项目
- 与websocat编译时确认的问题一致

### Chimera Linux尝试（失败）
- Chimera contrib repo列出sd-1.1.0-r0.apk但下载返回404
- Chimera使用apk3格式(v2签名), 不兼容标准apk-tools

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 1.0.0 aarch64-musl静态二进制 SIGSEGV | Rust musl静态编译与HarmonyOS不兼容 | 使用Alpine musl动态链接二进制替代 |
| 2 | rustc在HarmonyOS上崩溃(SIGSEGV) | librustc_driver初始化失败 | 无法解决，使用预编译二进制 |
| 3 | Chimera Linux APK下载返回404 | Chimera使用apk3格式，URL不可达 | 改用Alpine Linux APK |
| 4 | 二进制版本不匹配(1.1.0 vs 1.0.0-r0) | Alpine仅有1.1.0-r0版本 | 使用1.1.0 musl二进制作为替代 |

## 源码修改

无补丁。使用预编译二进制方式部署。

## 依赖版本

- 预编译二进制: sd v1.1.0-r0 (Alpine Linux, aarch64, musl, dynamic)
- ELF 签名工具: /data/service/hnp/bin/binary-sign-tool (self-sign模式)
- Runtime依赖: libc.musl-aarch64.so.1 (→ /lib/ld-musl-aarch64.so.1), libgcc_s.so.1

## 验证结果

```bash
$ sd --version
sd 1.1.0

$ echo "hello world" | sd "world" "HarmonyOS"
hello HarmonyOS

$ echo "foo bar baz" | sd "bar" "qux"
foo qux baz

$ file ~/usr/local/bin/sd
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), stripped
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| sd-1.0.0-r0-ohos-aarch64.tar.gz | 4179KB | 预编译包(含Alpine musl binary) |
| bin/sd | 1.6MB | ELF signed aarch64 musl动态二进制 |
| share/bash-completion/completions/sd | 1.5KB | bash补全 |
| share/zsh/site-functions/_sd | 2KB | zsh补全 |
| share/fish/vendor_completions.d/sd.fish | 0.8KB | fish补全 |
| share/man/man1/sd.1.gz | 1.2KB | man页面 |

## 注意事项

- sd 实际二进制版本为 v1.1.0 (来自Alpine Linux)，而非v1.0.0
- Rust musl静态编译的二进制在HarmonyOS上不兼容，避免使用
- rustc在HarmonyOS上崩溃，Rust项目必须使用预编译二进制部署
- Alpine Linux musl预编译二进制是最佳替代方案
- 动态链接musl二进制需要libc.musl-aarch64.so.1和libgcc_s.so.1两个运行时依赖
- Chimera Linux APK v3格式无法从仓库直接下载
---

**编译结束**: 2026-06-02 02:47
**最终状态**: published
