# rhai

## 简介

rhai 是用 Rust 实现的嵌入式脚本语言与求值引擎：面向 Rust 应用提供可沙箱化的脚本扩展能力，语法接近 JavaScript/Rust，纯 Rust、零 C 依赖、支持 `no_std` 与 WASM。上游同时提供三个可选命令行工具：`rhai-run`（脚本解释器）、`rhai-dbg`（脚本调试器）、`rhai-repl`（交互式 REPL，需 `bin-features`）。

## 功能概述

- **脚本执行**: `rhai-run script.rhai` 直接解释执行 `.rhai` 脚本
- **调试**: `rhai-dbg` 提供脚本调试接口（断点/单步，需 `debugging` 特性）
- **沙箱安全**: 可限制脚本可访问的 API、操作数与递归深度
- **嵌入能力**: 作为 Rust 库（rlib）嵌入宿主程序，支持 `#[export_module]` 注册原生函数
- **跨目标**: std / no_std（nightly）/ WASM / 多平台

## OHOS 适配

### 适配要点

- **构建系统**: Cargo workspace，配方内自管 `cargo build --release --bins --features debugging`
- **工具链**: 设备无 cargo/rustc，经 Conan `tool_requires` 引用制品仓 `rust-toolchain/1.97.1`（宿主与目标均为 aarch64-unknown-linux-ohos）
- **签名**: rust-lang dist 工具链（cargo/rustc/librustc_driver）与最终产物需 `binary-sign-tool -selfSign 1` 自签名，签名后须 `chmod +x`（OHOS 拒绝执行未签名 ELF）
- **sysroot**: `lib/rustlib` 必须真实复制，软链会导致 rustc 找不到 `std`
- **运行库**: cargo 动态链接 OpenSSL/zlib，用 harmonybrew OHOS bottle 并按 SONAME 提供实体文件 + 显式 `LD_LIBRARY_PATH`
- **crates 拉取**: rsproxy.cn sparse 镜像 + 设备 CA bundle（`SSL_CERT_FILE`）
- **PATH**: 需含 `/usr/bin`（OHOS SDK clang 包装脚本使用 readlink/dirname）
- **TMPDIR**: OHOS /tmp 只读，使用 `~/tmp` 等可写目录
- **依赖**: 无 C/C++ 依赖，仅以 OHOS SDK clang 作为链接器

### 已知问题

- 上游 `[patch.crates-io]` 将 rustlyine 指向第三方 git fork；配方已去除（仅影响未构建的 rhai-repl）

## 依赖关系

### 编译依赖

- rust-toolchain/1.97.1（Conan tool_requires，rust-lang 官方 dist 预编译 OHOS 工具链）
- Harmonybrew OHOS bottle：openssl@3-3.6.4_1、zlib-ng-compat-2.3.3_2（cargo 运行期库）

### 运行依赖

- 无特殊依赖（纯 Rust 产物；cli 二进制动态链接自身 libstd 与系统 libc）

## 参考资料

- 官网: https://rhai.rs
- 源码: https://github.com/rhaiscript/rhai
- crates.io: https://crates.io/crates/rhai
