# comet 0.3.2：HarmonyOS PC 适配

上游 imLinguin/comet 是 GOG Galaxy Communication Service 的开源实现（Rust/Cargo
应用，非 C/C++ 库），产出单个 `comet` 二进制（clap CLI + 本地网络服务）。仓内
Rust 包先例（cbindgen/0.28.0，rust-toolchain/1.97.1 真机 W3 PASS）证明该形态
可在 OHOS worker 构建；本包按同一路线适配。

## 固定源码与依赖

- 主源码：https://github.com/imLinguin/comet/archive/refs/tags/v0.3.2.tar.gz；
  tag v0.3.2；commit 3d7488ee72f83b7e8462a70fd4c4638d6da71360；
  SHA256 `5d619f3d801b5aceb6fe35489f94b8c59668b3b381048a65d7d30be21bc70838`。
- 第二源码（必带）：GitHub 自动归档不含 git 子模块 `proto`，而 build.rs 以
  `proto/*.proto`（10 个文件）为 protobuf 输入。固定 Yepoleb/gog_protocols
  commit 923e8a0 归档，解包到 `proto/`：
  https://github.com/Yepoleb/gog_protocols/archive/923e8a0008603365d29002db611559190da5bf99.tar.gz
  SHA256 `03fb8fa6c22b72f1b91a4008c6ae6dcc1f02a6201b09d37f070883c2aafa5de1`。
- 许可证 Apache-2.0（上游 LICENSE 全文；子模块归档内亦含 LICENSE，仅用于构建）。
- 无源码补丁（patches_applied 为空）：唯一上游阻塞文件 .cargo/config.toml 于
  source() 移除，见下文「原始失败与最小修复」第 1 条。
- Cargo.lock（344 crates）随源码固定，构建全程 `--locked`。依赖闭包无 OpenSSL：
  reqwest/rustls/tokio-tungstenite 均走 rustls（ring provider）；sqlx sqlite 走
  libsqlite3-sys bundled C 源码。锁图中 libc 0.2.171、ring 0.17.14 均已支持
  OHOS target_env（E358 风险未触发）。
- build 依赖（tool_requires，均已发布制品仓）：rust-toolchain/1.97.1（OHOS
  aarch64 原生工具链）、openssl/3.5.6.1.1（仅为 Cargo 本体重链私有 DSO）、
  protobuf/33.6（提供 OHOS 原生 protoc）。

## 原始失败与最小修复

1. 上游源码内 `.cargo/config.toml` 强制 `[target.aarch64-unknown-linux-gnu]
   linker = "aarch64-linux-gnu-gcc"`，在 OHOS worker 上不存在该交叉 linker。
   该段仅对 gnu 目标生效、与原生 OHOS 构建无关，source() 中直接移除该文件
   （scooter/0.9.1 移除 rust-toolchain.toml 同款做法；亦规避设备 toybox patch
   对无尾行 hunk 的兼容问题）；链接改由配方环境固定：`RUSTFLAGS=-C linker=<平台
   clang>` 与 `CARGO_TARGET_AARCH64_UNKNOWN_LINUX_OHOS_LINKER`（照 cbindgen 模式）。
2. build.rs（protobuf-codegen）需要可执行的 protoc：protoc-bin-vendored 自带的
   linux-aarch_64 二进制为 glibc 构建，无法在 OHOS (musl) 执行。build.rs 优先读
   `PROTOC` 环境变量，配方注入 protobuf/33.6 包内的 OHOS 原生 `bin/protoc`
   即可，无需改 build.rs（vendored 路径查找仅返回路径，不触发执行）。
3. rust-toolchain 发行二进制无 OHOS 执行签名、Cargo 动态依赖 libssl/libcrypto
   （E509）：沿用 cbindgen 已验证方案——构建期在私有缓存中复制并
   binary-sign-tool 自签 cargo/rustc/rustc_driver，PIC 静态 OpenSSL 重链为私有
   DSO，经 C 启动器 + Python helper（继承自 cbindgen，环境变量前缀 COMET_）
   注入受限 LD_LIBRARY_PATH 后 exec；不修改依赖包、不把 DSO 带入包产物。
4. OHOS worker 无 `cc`/`gcc`：CC/CXX 显式取自 profile 的
   tools.build:compiler_executables（clang），cc crate（ring/libsqlite3-sys bundled
   SQLite 的 C/汇编编译）与 rustc 链接均走该编译器，`ar` 由平台 PATH 提供。

## 上游测试（NO_UPSTREAM_TESTS）

上游无测试套件，证据链如下（discovery.status=EVIDENCE_COMPLETE）：

- v0.3.2 归档无 `tests/` 目录、无 `[[test]]` 段、无 dev-dependencies；
- 全部 `src/**/*.rs` 中 `#[cfg(test)]` 计数为 0；
- 上游 CI（.github/workflows/build.yml）仅 `cargo build`/clippy，无测试步骤；
- Alpine 社区包 APKBUILD 显式 `options="!check"`（注释：no tests）；
- release 资产仅为预编译二进制，无测试数据。

可信替代（已执行）：build() 内 `cargo test --locked --release --lib --bins`
形式执行（输出 running 0 tests；target 选择跳过 doctest——rust-toolchain 发行
包不含 rustdoc，与 cbindgen 相同）；test_package 以 3 项断言冒烟安装后的 CLI
（--version 精确匹配 `comet 0.3.2`、--help 用法面、未知参数拒绝）。

## 验证

环境：HarmonyOS PC aarch64（OpenHarmony 6.x）、HNP SDK、Clang 15（profile
指定）、Conan 2.29.1（OHOS 适配版）、官方 profile OHOS/6.0、armv8、Release、
libc++。

- 构建：`cargo build --locked --release`（rust-toolchain 1.97.1 原生工具链，
  CARGO_BUILD_JOBS 封顶 8）。
- 上游（形式）：`cargo test --locked --release --lib --bins` → 0 tests（上游本
  无测试）。
- 冒烟：`comet --version` → `comet 0.3.2`；`comet --help`；未知参数 exit≠0。
