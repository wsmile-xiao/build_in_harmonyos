# cargo-nextest

## 简介

cargo-nextest 是一个下一代 Rust 测试运行器，提供更快的测试执行、更好的测试报告和更丰富的功能。

## 功能概述

- **更快的测试执行**: 使用优化的测试调度策略，显著提升测试速度
- **改进的测试报告**: 提供详细的测试结果报告，包括失败测试的重放信息
- **测试分区**: 支持将测试集分区，便于并行执行
- **JUnit XML 输出**: 支持生成 JUnit XML 格式的测试报告
- **覆盖率集成**: 与 cargo-llvm-cov 无缝集成

## OHOS 适配

### 适配要点

- **构建系统**: 使用 Cargo 构建系统，无需 configure 步骤
- **编译命令**: `cargo build --release`
- **安装方式**: 将编译后的二进制文件复制到 `~/.cargo/bin` 或 `$PREFIX/bin`
- **静态链接**: Rust 程序通常静态链接标准库，依赖较少
- **ELF 签名**: 需要对生成的二进制文件进行 ELF 签名（鸿蒙要求）

### 已知问题

- 无已知问题

## 依赖关系

### 编译依赖

- rust (Rust 工具链，包括 cargo 和 rustc)

### 运行依赖

- 无特殊依赖（静态链接）

## 参考资料

- 官网: https://nexte.st
- 源码: https://github.com/nextest-rs/nextest
- 文档: https://nexte.st/docs