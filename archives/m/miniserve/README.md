# miniserve

轻量静态文件 HTTP 服务器（Rust）。适合快速在局域网分享目录：
目录浏览、归档下载（tar/tar.gz/zip）、文件上传、WebDAV、TLS、HTTP 认证、二维码访问链接。

- 上游仓库: https://github.com/svenstaro/miniserve
- 许可证: MIT
- 版本: 0.35.0

## 适配状态

| 版本 | 状态 | 构建系统 | 说明 |
|------|------|---------|------|
| 0.35.0 | published | cargo (Rust) | OHOS aarch64 原生编译，ELF 已签名 |

## 构建依赖

- rustc/cargo 1.97.1（OHOS 适配版，host = aarch64-unknown-linux-ohos）
- OHOS clang 15（linker + cc-rs C 依赖编译）
- crate 依赖全部来自 crates.io（actix-web 4.13.0 等），无系统 C/C++ 库依赖

## 使用

```bash
miniserve /path/to/dir --port 8080
```

参数示例：`--auth user:pass`、`--tls-cert` / `--tls-key`、`--enable-upload`、`--http2`、
`--qrcode`、`--upload` 等，详见 `miniserve --help`。

## 适配要点

1. 纯 Rust 应用，cargo 构建；rustc host 即 aarch64-unknown-linux-ohos，无需显式 --target。
2. C 依赖（zstd-sys 等）经 cc-rs 编译：CC/AR 指向 OHOS clang/llvm-ar。
3. rustc 默认 linker `cc` 在 OHOS 不存在，配方内设 CARGO_TARGET_..._LINKER 指向 OHOS clang。
4. OHOS ELF 必须用 binary-sign-tool 签名（-selfSign 1），否则运行报 Operation not permitted。
