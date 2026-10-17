# taskwarrior-tui 0.27.0 适配笔记

## 编译环境
- 构建系统: cargo (Rust, edition 2024)
- 编译日期: 2026-08-23
- 编译器: Harmonybrew Rust 1.97.1 (cargo/rustc)
- 状态: built

## 适配历史

### 历史编译 (2026-06-05)
- 在设备上使用 cargo 1.95.0 原生编译成功
- 未进行 Conan 适配，仅手动编译

### Conan 适配 (2026-08-23)
- 基于 cargo-bloat/0.12.1 的 Conan 配方模式
- 使用 Harmonybrew Rust 1.97.1 bottle 作为 OHOS CI 的 Rust 工具链后备
- 创建完整的 conanfile.py + conandata.yml + test_package/

## 编译步骤

1. **源码获取**：从 GitHub 下载 `v0.27.0` 标签源码包
2. **Rust 工具链**：OHOS 环境下从 Harmonybrew 下载 Rust 1.97.1 bottle（含 openssl、zlib、ca-certificates）
3. **Cargo 配置**：使用 rsproxy.cn 作为 crate 镜像源，配置 clang 为 linker
4. **编译**：`cargo build --release --locked`
5. **打包**：将 `taskwarrior-tui` 二进制复制到 `bin/`

## 源码修改

无源码修改，使用官方源码直接编译。

## 依赖版本

- Rust/Cargo: Harmonybrew Rust 1.97.1 bottle
- 运行时依赖: taskwarrior（未安装，仅影响功能测试，不影响编译）
- 编译依赖: 通过 Cargo.lock 管理的 Rust crate 依赖

## 注意事项

1. **Rust edition 2024**：需要 Rust 1.85+，Harmonybrew 1.97.1 满足要求
2. **运行时依赖**：taskwarrior-tui 需要 taskwarrior 才能完整使用
3. **构建系统**：这是 Rust/Cargo 项目，不是 autotools 项目
4. **build.rs**：生成 shell completions 和可选的 man pages（pandoc 不可用时非致命）
5. **CI 工具链**：OHOS CI 无 Rust 工具链，使用 Harmonybrew bottle 作为后备

## 参考配方

- cargo-bloat/0.12.1（相同 Rust 工具链 bootstrap 模式）
---

**编译结束**: 2026-08-23 00:44
**最终状态**: built
