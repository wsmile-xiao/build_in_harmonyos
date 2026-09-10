# bulletty 0.2.2 适配笔记

## 编译环境
- 构建系统: cargo（Rust edition 2024，rust-version 1.90）
- 编译日期: 2026-09-08
- 编译器: clang/clang++（OHOS SDK 26.0.0.18 LLVM 15）
- Rust 工具链: Harmonybrew rust 1.97.1 arm64_ohos bottle（桥接自举）
- 状态: built

## 编译步骤

```bash
# 1. Rust 工具链自举（OHOS runner 无 cargo/rustc）
curl -L -o rust.tar.gz https://harmonybrew.atomgit.com/bottles/rust-1.97.1.arm64_ohos.bottle.tar.gz
tar xzf rust.tar.gz   # 解压后修复 cargo wrapper 指向本地 cargo.real

# 2. cargo 源与交叉链接器配置（.cargo/config.toml）
#    source.crates-io → rsproxy-sparse (sparse+https://rsproxy.cn/index/)
#    [http] cainfo = 本机 CA 证书
#    [target.aarch64-unknown-linux-ohos] linker = /data/service/hnp/bin/clang

# 3. 交叉编译
export OHOS_SDK_NATIVE=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native
export CC=/data/service/hnp/bin/clang CXX=/data/service/hnp/bin/clang++
export RUSTFLAGS="-C linker=/data/service/hnp/bin/clang"
cargo build --release --target aarch64-unknown-linux-ohos --locked

# 4. 上游测试（72 处 #[test]，73 个用例）
cargo test --release --target aarch64-unknown-linux-ohos --locked
#     test result: ok. 73 passed; 0 failed; 0 ignored
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | aws-lc-sys 交叉编译缺符号（EVP_DigestFinal/EC_KEY_check_key 等 undefined） | reqwest 0.13 默认 `default-tls` 映射到 rustls 后端，其依赖 aws-lc-sys（BoringSSL）在 OHOS 交叉编译下静态库不完整 | Cargo.toml 中 reqwest 改用 `features=["blocking","native-tls-vendored","charset","http2","system-proxy"]`，复用已 vendored 的 OpenSSL，TLS 功能零损失 |
| 2 | cargo 拉取 crates 索引 SSL 证书验证失败 | 本机 CA 为自签名链 | .cargo/config.toml `[http] cainfo` 指向本机 cert.pem；环境变量 CARGO_HTTP_CAINFO/SSL_CERT_FILE |
| 3 | Harmonybrew cargo wrapper 指向不存在路径 | bottle 内 cargo wrapper 硬编码 /storage/Users/currentUser/.harmonybrew/Cellar/... | 修复 wrapper：`#!/bin/sh\nexec <本地>/cargo.real "$@"`（配方 _repair_wrappers） |
| 4 | rustc 启动缺 libc++_shared.so | rustc_driver 依赖 C++ 运行库 | LD_LIBRARY_PATH=/system/lib64（OHOS 系统自带） |

## 源码修改

补丁：0001-Cargo.lock.patch + 0002-Cargo.toml.patch（refresh-patch 拆分）
- Cargo.toml: reqwest 从默认（rustls）切换为 native-tls-vendored 后端
- Cargo.lock: 同步依赖图（移除 aws-lc-sys/aws-lc-rs/rustls/tinyvec 等，加入 tokio-native-tls/hyper-tls/native-tls）

## 依赖版本

- Rust 1.97.1（Harmonybrew bottle）
- OHOS SDK 26.0.0.18（clang 15.0.4）
- crates: reqwest 0.13.4、openssl 0.10.75（vendored）、native-tls 0.2.18、hyper-tls 0.6.0、tokio-native-tls 0.3.1

## 验证结果

```bash
bulletty --version   # bulletty 0.2.2 （rc=0）
bulletty --help      # 完整 CLI 帮助
bulletty dirs        # Library: .../bulletty, Logs: .../bulletty_logs
cargo test（OHOS 交叉）: 73 passed; 0 failed
test_package: 3/3 断言通过（version/help/dirs）
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/bulletty | 19.4MB 静态 ELF（aarch64-unknown-linux-ohos，musl loader） |

## 注意事项

- OHOS runner 无 cargo/rustc，必须使用 conandata.yml 的 rust_toolchain bottles 自举
- reqwest 后端切换不影响任何 TLS 功能（同为 HTTPS 客户端实现）
- 上游测试全部在 src/ 内嵌（无 tests/ 目录），73 个用例在交叉构建中真实运行
---

**编译结束**: 2026-09-09 13:22
**最终状态**: built
