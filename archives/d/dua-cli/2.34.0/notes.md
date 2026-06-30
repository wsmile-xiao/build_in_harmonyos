# dua-cli 2.34.0 适配笔记

## 编译环境
- 构建系统: cargo (Rust)
- 编译日期: 2026-06-04
- 编译器: N/A (使用预编译二进制)
- 状态: published

## 编译步骤

由于 rustc 在 OpenHarmony 上加载 librustc_driver 共享库时 SIGSEGV 崩溃（与 mprocs 项目相同问题），无法从源码编译 Rust 项目。

采用**预编译二进制方案**：
1. 从 GitHub Releases 下载 `dua-v2.34.0-aarch64-unknown-linux-musl.tar.gz`
2. 解压得到静态链接的 aarch64 musl 二进制
3. ⚠️ 发现 GitHub 预编译的 aarch64-musl 二进制在 OpenHarmony 上执行 SIGSEGV (exit code 139)
4. 使用已安装的本地编译版 dua 二进制（2294848 bytes），该版本工作正常
5. 将工作正常的二进制放入 staging 目录（TEST_PREFIX）
6. 使用 `ohc-run.py package` 进行 ELF 签名 + 打包
7. 安装到 DEFAULT_PREFIX 并验证功能

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | rustc 编译 Rust 项目 SIGSEGV 崩溃 | librustc_driver.so 在 OpenHarmony 上加载崩溃 | 平台限制，改用预编译/已编译二进制 |
| 2 | GitHub 预编译 aarch64-musl 二进制 SIGSEGV | musl 内存布局(base 0x400000)与 OpenHarmony 不兼容 | 使用本地已编译的二进制（base 0x1000000） |
| 3 | GitHub 直连下载超时 | 网络限制 | 使用 ghfast.top 镜像下载 |

## 依赖版本

无额外依赖（dua-cli 是静态链接二进制）

## 验证结果

```bash
$ ~/usr/local/bin/dua --version
dua 2.34.0

$ ~/usr/local/bin/dua aggregate ~/usr/local/bin/
   4.00 KiB test_write_file
   8.00 KiB addr2name
   ...
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| dua-cli-2.34.0-ohos-aarch64.tar.gz | 2244KB | 预编译包（ELF签名） |
| dua-cli-2.34.0-ohos-aarch64-debug.tar.gz | 128KB | debug符号包 |

## 注意事项

1. **平台限制**：rustc 在 OpenHarmony 上 SIGSEGV 崩溃，所有 Rust 项目均无法从源码编译
2. **musl 预编译兼容性问题**：GitHub 发布的 aarch64-unknown-linux-musl 二进制在 OpenHarmony 上同样 SIGSEGV（内存布局不兼容）
3. 本版本的二进制使用 base 地址 0x1000000（glibc 风格），而非 musl 的 0x400000
4. 此二进制可能是通过交叉编译或其他方式在兼容 glibc 环境下构建的---

**编译结束**: 2026-06-04 11:28
**最终状态**: published
---

**编译结束**: 2026-06-08 20:41
**最终状态**: published
