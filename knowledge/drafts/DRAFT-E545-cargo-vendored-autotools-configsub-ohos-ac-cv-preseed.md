# DRAFT: cargo 内置 autotools C 子构建（如 tikv-jemalloc-sys）config.sub 不识 ohos —— ac_cv_* 预置免改上游

- **草稿 ID**: DRAFT-E545-cargo-vendored-autotools-configsub-ohos-ac-cv-preseed
- **来源库**: rumdl 0.2.39（Rust/cargo；OHOS PC aarch64，clang 15 / OHOS SDK 26.0.0.18，tool_requires rust-toolchain/1.97.1）
- **状态**: 草稿（待主编 promote 为正式 E 条目）
- **同族条目**: E007（平台三元组）、E205 / E268（config.sub 加 linux-ohos）、E385（Cargo CMake 子构建补 llvm-ranlib）

## 错误特征

`conan create` 构建纯 Rust 工具时，首个真实错误来自 crate 内置的 autotools 子构建：

```
configure: exit 1
--- stderr
Invalid configuration `aarch64-unknown-linux-ohos': OS `ohos' not recognized
configure: error: /bin/sh build-aux/config.sub aarch64-unknown-linux-ohos failed

thread 'main' panicked at tikv-jemalloc-sys-0.6.1+5.3.0-.../build.rs:411:9:
command did not execute successfully: ... configure --host=aarch64-unknown-linux-ohos --build=aarch64-unknown-linux-ohos ...
```

## 触发条件

- 构建系统: **cargo**（crate 的 `build.rs` 调用其内置 C 依赖的 autotools `configure`）
- 阶段: build
- 典型 crate: `tikv-jemalloc-sys`（`tikv-jemallocator` 在非 msvc/non-wasm 目标上**强制**作为全局分配器）；其它 bundle 了 `configure` 的 `-sys` crate
- 关键区别: 源码位于 `$CARGO_HOME/registry/src/**`，每次构建由 `.crate` 重新解压 → **不能**像原生 autotools 包那样 patch `config.sub`

## 根因分析

crate bundle 的 `config.sub`（jemalloc 自带）早于 `ohos`，`configure --host=aarch64-unknown-linux-ohos` 无法把三元组规范化为可识别系统。原生 autotools 包的惯用修法（E007 脚本 / E205/E268 给 `config.sub` 加 `linux-ohos`）对 **cargo-vendored** 依赖不成立：vendored 源码是只读缓存、且随 crate 重解压，任何源码补丁都不持久、不可复现。

## 解决方案

### 推荐方案：预置 autoconf 规范化三元组缓存（零源码修改）

autoconf 的 `AC_CANONICAL_*` 在 **cache 变量 `ac_cv_build`/`ac_cv_host`/`ac_cv_target` 已设置时跳过 `config.sub`**。把它们预置为目标三元组的 `-musl` 变体（OHOS = musl Linux；`host_os` 仍匹配 jemalloc 的 `linux*` 分支）：

```bash
export ac_cv_build=aarch64-unknown-linux-musl
export ac_cv_host=aarch64-unknown-linux-musl
export ac_cv_target=aarch64-unknown-linux-musl
export CC_aarch64_unknown_linux_ohos=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/aarch64-unknown-linux-ohos-clang
cargo build --release --locked --target aarch64-unknown-linux-ohos
```

复现/验证：

```bash
# 未预置（失败）
sh ./configure --host=aarch64-unknown-linux-ohos --build=aarch64-unknown-linux-ohos   # → OS `ohos' not recognized
# 预置后（通过）
env ac_cv_build=aarch64-unknown-linux-musl ac_cv_host=aarch64-unknown-linux-musl ac_cv_target=aarch64-unknown-linux-musl \
    sh ./configure --host=aarch64-unknown-linux-ohos --build=aarch64-unknown-linux-ohos   # → rc=0，"checking host system type... (cached) aarch64-unknown-linux-musl"
```

### 回退方案

改用制品仓已适配的 `jemalloc`/系统分配器并令 `build.rs` 走 `JEMALLOC_OVERRIDE`。代价：需保证符号前缀与编译选项一致，且引入额外 C 依赖，通常不必要。

### 禁止做法

- ❌ `sed -i`/patch `build-aux/config.sub` —— vendored 源码随 crate 重解压，补丁丢失，本地绿 CI 红。
- ❌ 用假的 `--build`/`--host` 三元组绕过 —— E007 明令：会翻成 `cross_compiling=yes`，跳过 `AC_RUN_IFELSE`，`config.h` 失真。
- ❌ 通过 `--no-default-features` 关闭默认分配器 —— `tikv-jemallocator` 是**目标条件依赖**（`cfg(all(not(target_env="msvc"), not(target_arch="wasm32")))`），非 feature，无法关闭。

## 关联条目

- 相关: E007（平台三元组）、E205 / E268（config.sub 加 linux-ohos）、E385（Cargo CMake 子构建补 llvm-ranlib）、E011/E112（HMDFS 下 config.status mktemp 不可写）
