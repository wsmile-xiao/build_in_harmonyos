# DRAFT-rust-workspace-slice-build-monorepo

## 症状

Cargo monorepo（workspace 根在仓库根）在 OHOS 真机/CI 沙盒 conan create 的
build() 内执行裸 `cargo build` 时，进度停在依赖解析：

```
    Updating git repository `https://github.com/signalapp/boring`
```

或更深一层：

```
    Updating git submodule https://github.com/google/boringssl.git
```

无报错、无超时上限，只能整轮强杀。实例：libsignal-core/0.103.1 适配真机第 1 轮
（2026-09-27，signalapp/libsignal 25 成员 monorepo）。

## 根因

- workspace 的 `[workspace]` 表在仓库根：目标 crate（rust/core）**不在**
  `members` 显式列表（25 成员均未含它），而是经 `workspace.dependencies` 的
  path 依赖**隐式入图**。裸 `cargo build` = 构建全部成员，每个成员各自的 git
  依赖（bridge/* 的 boring-signal / SparsePostQuantumRatchet 等）都被 fetch。
- OHOS 设备与 CI 沙盒无法访问 github，git fetch 无超时上限 → 永久挂起。
- 第二卡点：`[patch.crates-io]` 段的 git 补丁源在**依赖解析期**就执行 git
  fetch——即使目标切片根本不需要该补丁 crate（真机第 2 轮实证：-p 切片后
  仍卡在 "Updating git repository signalapp/boring"）。

## 修复（三件套之 ①②）

1. 构建命令显式切片：`cargo build --release -p <crate> --locked`；
2. 补丁缩容 workspace：`members = ["<crate>"]`（default-members 同缩）、删除
   其他成员的 git workspace 依赖行、删除 `[patch.crates-io]` 的 git 源（改
   registry 源或整体删段）→ 解析图零 git 依赖，即使重解析也只走可直连的
   registry 镜像（rsproxy.cn sparse）。

实例：libsignal-core/0.103.1 补丁 0001（25→1 成员 + 删 3 个 git workspace
依赖 + 删 patch 段），真机第 6 轮 cargo 零 git 解析实证，直接编译 registry
crate（zerocopy 0.8.53 / thiserror 2.0.18 / derive_more 2.1.1 等上游钉版）。

## 适用范围

- 一切 workspace 根不在 crate 自身目录、目标 crate 非 members 显式成员的
  Cargo monorepo 配方（应用与库均可触发）；
- 单 crate 仓库无此问题（仓内先例：argc/1.24.0 等 8 个已合入 Rust 包）。

## 反例/边界

- 目标 crate 恰在 members 列表且无其他成员的 git 依赖：`-p` 即可，无需缩容；
- 若目标 crate **直接**依赖 git 源且无法删除：只能走 fallback——git 仓库内容
  vendor 进源码树，补丁把依赖声明改写为 path 依赖，离线化解析图；
- 非本机理的 fetch 卡死：registry 源本身不可达（改 sparse 镜像，见仓内
  net 容错先例）。

## 触发实例

- libsignal-core/0.103.1（2026-09-27/28）：第 1 轮裸 build 卡 boring →
  -p 切片 → 第 2 轮卡 patch 段 git 源 → 缩容 + 删 patch 段 → 第 6 轮零 git
  解析，build + package 成功（34 rlibs）。

## 相关

- DRAFT-rust-toolchain-no-rustdoc-skip-doctests：Rust on OHOS 工具链族
  （测试目标限定面）；
- wagyu-0.6.1-rust-legacy-lockfile-ohos-port：legacy lockfile 迁移；
- DRAFT-rust-workspace-lockfile-desync-git-clone-hang：本条的姊妹篇——切片后
  仍可能因 Cargo.lock 失配触发全 workspace 重解析而卡 git，须三件套齐用。
