# DRAFT-rust-toolchain-file-vs-msrv-pinning

## 症状

OHOS 环境（自举 Harmonybrew rust bottle，无 rustup）直调 cargo 构建带
rust-toolchain 文件的上游 Rust 包时，出现两类现象：

1. **静默漂移**：构建/测试全程零报错，但实际用的 rustc 版本与上游钉版
   不一致（本机 rustup 用户无感，真机/CI 才暴露）；
2. **MSRV 触顶**：用低版本工具链构建时报
   `error: package '...' cannot be built because it requires rustc 1.93.1 or newer, while the currently active rustc version is ...`。

实例：libsignal-core/0.103.1 适配（上游 rust-toolchain 钉 1.98.1、
rust/core Cargo.toml rust-version=1.93.1，2026-09-28）。

## 根因

两个机制语义不同，混用必踩：

- **rust-toolchain 文件**（channel/toml 两格式）是 **rustup 的约定**：
  rustup 包装的 cargo 读它选工具链；**直调 cargo 二进制**（不经 rustup，
  如 bottle 的 cargo.real）时该文件被完全忽略——不报错、不自动切换。
- **rust-version 字段**（MSRV）由 **cargo 自身强制**：目标 crate 或其任一
  依赖的 rust-version 高于当前 rustc 时编译直接报错。

所以直调路径上版本钉扎只有 rust-version 这一道硬约束；rust-toolchain 钉版
必须由配方自己读取并自举对应版本，否则漂移是静默的。

## 修复

- 配方读取上游 rust-toolchain 文件取钉版，**自举工具链就用该版本**
  （Harmonybrew bottle 版本以 formula 仓库 current revision 为准——旧 URL
  随镜像换代 404 是常态，真机轮会原形毕露）；
- 同时确认钉版 ≥ 依赖闭包最大 rust-version（cargo metadata 枚举取最大）；
- 全链加 --locked 兜底锁图，防止解析期二次漂移。

实例：libsignal-core 自举 1.98.1（= rust-toolchain 钉版）bottle，MSRV
1.93.1 ≤ 1.98.1，构建/测试全程零版本告警。

## 适用范围

- 一切在 OHOS 环境经自举工具链（无 rustup）直调 cargo 的 Rust 配方；
- 上游仓库根带 rust-toolchain 文件时风险最高。

## 反例/边界

- 钉版 bottle 已被镜像清理：fallback = 自举 ≥ 依赖闭包最大 rust-version
  的最新在服版本，但须如实标注"工具链版本 ≠ 上游钉版"及差异评估；
- rustup 存在且网络可达的环境：rust-toolchain 文件自动生效，本坑不触发；
- edition（2021/2024）与 MSRV 是两个独立约束——edition 由 Cargo.toml 声明、
  rustc 硬校验，与 rust-toolchain 文件无关。

## 触发实例

- libsignal-core/0.103.1（2026-09-28）：自举 1.98.1 bottle 直调 cargo，
  实证直调路径只有 rust-version 生效，版本一致性与上游对齐。

## 相关

- DRAFT-below-ohos-unsigned-rust-toolchain：OHOS 自举工具链基础；
- DRAFT-rust-toolchain-no-rustdoc-skip-doctests：同工具链的组件缺失面；
- DRAFT-rust-workspace-lockfile-desync-git-clone-hang：--locked 兜底的必要性。
