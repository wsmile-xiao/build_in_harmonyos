# AES 0.7.4 适配笔记

## 软件信息

- **软件名**: aes
- **版本**: 0.7.4
- **上游仓库**: https://github.com/RustCrypto/block-ciphers
- **标签**: aes-v0.7.4
- **描述**: Pure Rust implementation of the Advanced Encryption Standard (a.k.a. Rijndael)
- **许可证**: MIT OR Apache-2.0
- **构建系统**: Cargo (Rust)
- **源码位置**: /storage/Users/currentUser/builds/aes-0.7.4.work/

## 源码结构

```
aes/
├── Cargo.toml          # 包定义，依赖 cipher/cfg-if/ctr/opaque-debug/cpufeatures
├── Cargo.lock          # 依赖锁定文件
├── README.md           # 项目说明
├── CHANGELOG.md        # 变更日志
├── LICENSE-APACHE      # Apache-2.0 许可证
├── LICENSE-MIT         # MIT 许可证
├── benches/            # 性能基准测试
│   ├── aes128.rs
│   ├── aes192.rs
│   └── aes256.rs
├── src/
│   ├── lib.rs          # 库入口，定义 Aes128/Aes192/Aes256 结构体
│   ├── autodetect.rs   # 运行时后端自动检测
│   ├── soft.rs         # 软件后端入口
│   ├── soft/
│   │   ├── fixslice32.rs  # 32位 fixslice 软件实现
│   │   ├── fixslice64.rs  # 64位 fixslice 软件实现
│   │   └── ctr.rs         # 软件 CTR 模式
│   ├── ni.rs           # AES-NI 硬件后端
│   ├── ni/
│   │   ├── aes128.rs, aes192.rs, aes256.rs  # NI 特定实现
│   │   ├── ctr.rs, hazmat.rs, utils.rs
│   ├── armv8.rs        # ARMv8 硬件后端
│   │   ├── decrypt.rs, encrypt.rs, expand.rs, hazmat.rs
│   └── hazmat.rs       # 底层 hazardous API
└── tests/
    ├── lib.rs, ctr.rs, hazmat.rs
    └── data/           # NIST 测试向量 (.blb 二进制文件)
```

## OHOS 适配分析

### 1. Rust 工具链问题

**核心问题**: OpenHarmony 系统上 Rust 工具链完全不可用。

- `cargo` 二进制文件存在但无法运行，报 200+ 个 OpenSSL 符号未找到错误
- `rustc` 不存在
- `rustup` 未安装，终端网络受限无法下载安装

**根因分析**: cargo 二进制文件编译时链接了特定版本的 OpenSSL，而 OpenHarmony 系统提供的 `/usr/lib/libcrypto.so.3` 和 `/usr/lib/libssl.so.3` 版本不兼容。

**可能的解决方案**:
1. 从源码编译 Rust 工具链（需要 C 编译器和大量时间）
2. 交叉编译 Rust 工具链到 aarch64-unknown-linux-ohos
3. 等待 OpenHarmony 官方提供 Rust 工具链支持

### 2. 源码分析

AES 0.7.4 是纯 Rust 实现，无 C/C++ 依赖。关键特性：

- **force-soft**: 禁用硬件加速，使用 fixslice 纯软件实现
  - fixslice32: 针对 32 位优化的 bitsliced 实现
  - fixslice64: 针对 64 位优化的 bitsliced 实现
- **armv8**: 使用 ARMv8 AES 指令（AESE, AESD, AESMC, AESIMC）
- **ni**: 使用 x86 AES-NI 指令
- **autodetect**: 运行时检测 CPU 特性，自动选择最佳后端

在 OpenHarmony/aarch64 上，理想配置是使用 `armv8` 特性（利用硬件 AES 指令）或 `force-soft`（纯软件回退）。

### 3. 依赖分析

| 依赖 | 版本 | 类型 | 说明 |
|------|------|------|------|
| cfg-if | 1 | 普通 | 编译时条件判断宏，纯 Rust |
| cipher | 0.3 | 普通 | 分组密码 trait 定义，纯 Rust |
| ctr | 0.7 | 可选 | CTR 模式实现，纯 Rust |
| opaque-debug | 0.3 | 普通 | Debug trait 辅助，纯 Rust |
| cpufeatures | 0.1.4 | 条件依赖 | CPU 特性检测，aarch64/x86_64/x86 时引入 |

所有依赖均为纯 Rust 实现，无系统库依赖。这意味着一旦 Rust 工具链可用，AES 0.7.4 应该可以顺利编译。

### 4. C 验证实现

由于 Rust 工具链不可用，编写了 C 语言等效 AES 实现（`aes_verify.c`）进行算法验证：

- 实现了完整的 AES-128/192/256 加密和解密
- 使用 FIPS 197 Appendix B 标准测试向量验证 AES-128
- 使用全零密钥测试向量（与 RustCrypto 测试一致）
- AES-192/256 使用往返测试验证加解密一致性
- 编译器: `/data/service/hnp/bin/aarch64-unknown-linux-ohos-clang`
- 全部 9 项测试通过

## 适配状态

| 项目 | 状态 | 说明 |
|------|------|------|
| 源码下载 | ✅ 完成 | 通过 webFetch 从 GitHub raw 下载 |
| Rust 编译 | ❌ 失败 | Rust 工具链不可用 |
| 算法验证 | ✅ 通过 | C 语言等效实现，9/9 测试通过 |
| 归档文件 | ✅ 完成 | manifest.yaml, test-report.md, notes.md, quality-report.md |

## 后续建议

1. **安装 Rust 工具链**: 一旦网络可用，通过 rustup 安装 Rust 工具链，然后执行 `cargo build --release --features force-soft` 和 `cargo test --features force-soft`
2. **测试 ARMv8 后端**: OpenHarmony/aarch64 平台应测试 `--features armv8` 是否可以利用硬件 AES 指令
3. **运行 RustCrypto 原生测试**: `cargo test` 将运行 tests/ 目录下的 NIST 测试向量（.blb 二进制文件）
