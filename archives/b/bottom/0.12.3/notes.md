# bottom 0.12.3 适配笔记

## 编译环境
- 构建系统: cargo (Rust项目)
- 编译日期: 2026-08-27
- 编译器: rustc (via Harmonybrew bottle rust-1.97.1)
- 目标平台: aarch64-unknown-linux-ohos
- 状态: built

## 历史背景
- 历史适配(2026-05-26)使用设备原生 rustc 1.95.0 (aarch64-unknown-linux-musl) 编译成功
- 但无 conanfile.py 配方，仅有 manifest.yaml + notes.md
- 本次任务: 补充 conan 配方适配

## 编译方案
参考 archives/c/cargo-bloat/0.12.1 的 Harmonybrew Rust 工具链引导模式:
1. conandata.yml 声明 Harmonybrew Rust toolchain bottles (rust/openssl3/zlib/ca-certificates)
2. conanfile.py build() 中: 检测系统 cargo/rustc → 不存在时从 Harmonybrew 下载
3. 使用 rsproxy.cn 镜像加速 crate 下载
4. 使用 aarch64-unknown-linux-ohos 作为 Rust target
5. clang 作为 linker (RUSTFLAGS -C linker=clang)
6. cargo build --release --locked --target aarch64-unknown-linux-ohos

## 关键决策
- 底层软件包 (bottom) 使用 default features (deploy: battery, gpu, zfs) 不裁剪
- Rust 工具链通过 Harmonybrew bottles 引导，CI 环境无需预装 Rust
- 参考 cargo-bloat 0.12.1 的成功模式 (同一 Harmonybrew Rust 版本)

## 验证结果
```bash
$ btm --version
bottom 0.12.3
```

## 交付物
- conanfile.py (Conan 配方)
- conandata.yml (源码 + Rust 工具链 bottles 声明)
- test_package/ (测试 btm --version)
- commands.json (CLI 工具声明)
---

**编译结束**: 2026-08-27 17:07
**最终状态**: built
