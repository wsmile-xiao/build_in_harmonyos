# DRAFT-rust-workspace-lockfile-desync-git-clone-hang

## 症状

打补丁改了 Cargo.toml（删 patch 段、删 dev-deps、缩成员……）后，随附上游
原版 Cargo.lock，真机/CI 构建仍卡死：

```
    Updating git submodule https://github.com/google/boringssl.git
```

**最迷惑的点**：补丁明明已经把 git 依赖删掉了，cargo 还是去拉。实例：
libsignal-core/0.103.1 适配真机第 5 轮（2026-09-27，patch 段与 dev-deps
已删，仍卡 "Updating git submodule boringssl"）。

## 根因

- **Cargo.lock 是 workspace 级锁**：记录整个 workspace 的解析图，不是单个
  crate。任一成员 manifest 与锁**任何失配**（增删成员、改 dev-deps、动
  patch 段……）→ cargo 放弃锁、**重解析整个 workspace**。
- 重解析时解析器必须读取**其他成员**（含本次构建根本不需要的成员）的
  manifest；这些成员经 workspace.dependencies 直连 git 依赖（bridge/* 的
  boring-signal 含 boringssl 子模块、spqr）→ 解析器克隆这些 git 仓库。
- OHOS 设备/CI 无 github 访问、git fetch 无超时上限 → 永久挂起。
- 排障误区：删掉 git 依赖 ≠ 消灾——**随附的原版锁与改动后 manifest 失配
  本身就是重解析触发器**，重解析走全 workspace 成员图。

## 修复（三件套，缺一不可）

1. **缩 workspace 到切片**：members=["<crate>"] + 删其他成员的 git
   workspace 依赖 + 删 [patch.crates-io] git 源 → 解析图零 git 依赖；
2. **随附重生成的 Cargo.lock**：从上游原锁抽目标 crate 依赖闭包，再
   `cargo update --precise` 把 cargo 抬高的包逐包钉回上游原锁版本（零漂
   移；feature 收缩正当剔除的包如实记录），`cargo check --locked` 实证锁
   即当前；
3. **全链 --locked**：一旦失配立即报错，而不是静默克隆 github 卡死。

实例：libsignal-core 补丁 0001（98 包闭包 + 27 包 --precise 钉回 + 18 包
feature 收缩剔除），真机第 6 轮零 git 解析，直接编译上游钉版（zerocopy
0.8.53 / thiserror 2.0.18 / derive_more 2.1.1）。

## 适用范围

- 一切"打补丁改 manifest + 随附上游原版 Cargo.lock"的 Cargo monorepo
  配方；
- 单 crate 仓库失配只重解析自身闭包（无其他成员的 git 依赖），风险低一档。

## 反例/边界

- git 依赖删不掉（目标切片直接依赖）：fallback = vendor 进源码树改 path
  依赖，锁随 path 重新生成，解析图完全离线；
- 纯 registry 依赖的 workspace：失配重解析不卡 git，但会静默漂移版本——
  --locked 同样是必加兜底；
- 该坑与切片坑（DRAFT-rust-workspace-slice-build-monorepo）是姊妹篇：
  切片解决"构建全量成员"，本条解决"失配重解析走全 workspace 图"——两者
  必须同时处置。

## 触发实例

- libsignal-core/0.103.1（2026-09-27/28）：第 5 轮删 patch/dev-deps 后仍
  卡 boringssl → 根因定位为锁失配 → 三件套 → 第 6 轮零 git 解析。

## 相关

- DRAFT-rust-workspace-slice-build-monorepo：姊妹篇（切片构建面）；
- wagyu-0.6.1-rust-legacy-lockfile-ohos-port：锁文件版本迁移；
- DRAFT-rust-toolchain-file-vs-msrv-pinning：--locked 兜底与工具链钉扎的
  组合必要性。
