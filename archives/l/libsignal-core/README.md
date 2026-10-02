# libsignal-core — 鸿蒙PC适配

Signal Messenger 的 libsignal monorepo 中的核心身份/密钥原语库（rust/core crate，
crate 名 libsignal-core，AGPL-3.0-only）：ServiceId/Aci/Pni、E164、DeviceId、
ProtocolAddress、curve（X25519 密钥对与签名）。workspace 根在仓库根，rust/core
靠 workspace.dependencies path 依赖隐式入图，构建用 `cargo build -p libsignal-core`
切片选建。

## 交付形态

本包是本仓库首个 Rust「库」包（此前 argc 等 8 个已合入 Rust 包均为 application），
交付 **rlib 静态归档闭包**：

- `lib/liblibsignal_core.rlib` + `lib/liblibsignal_debug.rlib` + 全部传递依赖 rlib
  （哈希后缀名，**平铺**在 lib/ 顶层——rustc -L dependency 只在单一目录解析
  哈希名 rlib，deps/ 子目录不会被搜索，故 package() 把 target/release/deps/
  的哈希 rlib 与顶层 rlib 一起平铺拷贝进 lib/）+ 传递依赖中的 proc-macro
  crate .so（zerocopy_derive 等，元数据在 .so 内，消费者全图元数据加载必需，
  真机第 7 轮实证缺失时 probe 报 can't find crate）

Rust 消费者直接链接：

```
rustc --edition 2024 \
  --extern libsignal_core=$pkg/lib/liblibsignal_core.rlib \
  -L dependency=$pkg/lib probe.rs
```

## 适配要点

- 工具链：探测已知 cargo 位置，无则 urllib 自举 Harmonybrew rust-1.98.1 bottle
  （argc/1.24.0 同仓库先例；bottle 版本会随镜像换代过期，以 Harmonybrew formula
  仓库 current revision 为准）；1.98.1 = 上游 rust-toolchain 文件钉的版本，
  依赖 MSRV ≤ 1.93.1
- 补丁 0001：workspace 缩容到 rust/core（删 25 成员/3 个 git workspace 依赖/
  [patch.crates-io] 段/4 个零引用 dev-deps）+ 随附重生成的 Cargo.lock（逐包
  --precise 钉回上游原锁版本，零漂移）——Cargo.lock 是 workspace 级锁，任何
  manifest 失配都会触发全 workspace 重解析并克隆 bridge 成员的 git 依赖
  （真机实证卡死在 boringssl 子模块），缩容+随锁+--locked 三件套后真机
  cargo 零 git 解析
- 上游测试：cargo test -p libsignal-core --lib --release（25 个 src 单测）在
  test_package 阶段执行并打印 HMBS_UPSTREAM_TEST_RESULT

详细适配记录见 `0.103.1/notes.md`。
