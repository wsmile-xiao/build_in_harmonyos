# zram 1.2.1 适配笔记（上游 systemd/zram-generator）

## 上游与版本

- 项目：systemd/zram-generator v1.2.1（2024-11-28 发布，MIT），Rust edition 2021 纯 crate，无 C 源码
- 源码：GitHub tag tarball，SHA256 `9c82cd3db386e82fba2adfe01c3d09436c9e9cfe3ca8bb341d7eb882768c58af`（真机下载实测一致，30,403 字节）
- 注意：不用 crates.io .crate（上游 Cargo.toml `exclude` 了部分 tests/，两种归档内容不同）
- 身份说明：ecdye/zram-config 亦有 v1.2.1 tag；本 run 判定为 systemd/zram-generator（发行版标准实现、当前最新 release；Scout 已做歧义披露）
- 上游 v1.2.1 无 meson，纯 Makefile 包 cargo；上游仓库无 Cargo.lock，cargo 按 Cargo.toml 解析最新兼容版本

## 构建方案

- recipe 名 `zram`（run 指定），产物 `zram-generator` 可执行 → `bin/`；`zram-generator.conf.example` 文档级保留 → `share/doc/zram-generator/`
- 上游 Makefile `program` 目标 + make 命令行变量覆盖（零 Makefile 补丁）：

  ```
  make -C <src> program NOMAN=1 CARGO=<cargo> \
    SYSTEMD_UTIL_DIR=/usr/lib/systemd \
    SYSTEMD_SYSTEM_GENERATOR_DIR=/usr/lib/systemd/system-generators \
    SYSTEMD_SYSTEM_UNIT_DIR=/usr/lib/systemd/system
  ```

  - `SYSTEMD_UTIL_DIR := $(shell pkg-config --variable=systemdutildir systemd)` 硬门被命令行变量覆盖（GNU make 命令行变量优先于文件内 `:=` 赋值，pkg-config 不再执行）；三个 `SYSTEMD_*` 变量全量覆盖以消除 `$(shell pkg-config)` 日志噪音
  - `NOMAN=1` 跳过 ronn man 页；不调用 `systemd-service`/`install` 目标（不装 systemd unit）
  - `SYSTEMD_UTIL_DIR` 被 Makefile `export` 进 cargo 环境：`src/setup.rs` 以 `env!("SYSTEMD_UTIL_DIR")` 编译期内联（`SYSTEMD_MAKEFS_COMMAND` 与 `--help` 的 AFTER_HELP 文本），值缺失即编译失败——占位 `/usr/lib/systemd` 为发行版惯用 util 目录
- 唯一补丁 `patches/0001-gate-nix-devdep-for-ohos.patch`（conandata 声明、source() 经 apply_conandata_patches 应用）：dev-dependencies 的 nix 按 `cfg(not(target_env = "ohos"))` 门控。原因链（真机/源码双侧定位）：
  - nix 0.23.2 的 pre-ohos cfg 门 `all(target_os = "linux", not(target_env = "musl"))`（fcntl.rs:88-93 O_FSYNC；lib.rs mqueue/aio 模块）在 target_env="ohos" 上误判为非 musl，启用 glibc-only 符号；
  - libc 的 musl 模块（ohos 目标路由至此）没有 O_FSYNC/mq_*/aio_*（对 libc 0.2.139…0.2.189 逐版本源码核实），任何 libc 版本固定都无法满足——真机实测 51 个编译错误；
  - 上游声明范围 `nix >=0.22, <0.24` 内无 ohos 感知版本（nix 0.26.4 同样存在该 cfg 门），ohos 修复在 nix >=0.27，但 0.27 移除了集成测试辅助代码用的 mount API；
  - cargo 对 `--bins` 测试目标同样构建 dev-deps 图，故门控是 `cargo test --lib --bins` 可编译的前置条件；补丁仅调整依赖解析的目标适用范围，不改动任何上游测试用例与断言，非 OHOS 平台行为与上游完全一致。
- cargo 环境（argc/1.24.0 先例）：`CC`/`CXX`=clang、`RUSTFLAGS='-C linker=clang'`；`.cargo/config.toml` 写源码根（`[target.aarch64-unknown-linux-ohos]` linker + rsproxy.cn sparse 镜像 + retry/timeout 容错；target-dir 绝对路径指向源码根 target/）
- 工具链探测：`~/.harmonybrew/bin/cargo`（优先 `.real` 真身，绕开 Harmonybrew Cellar 硬编码 wrapper）；缺失时引导（2026-10 返修）：rustc/std 取 Harmonybrew rust 1.99.0 bottle，cargo 取官方 rust dist ohos 组件并用 binary-sign-tool selfSign 签名（HMDFS 只执行带 .codesign 的 ELF；1.99.0 bottle 的 cargo 依赖闭包不可满足且旧版 bottle 已下架），openssl3/zlib-ng-compat/zstd bottle 供 libssl/libcrypto/libz/libzstd
- HMDFS ETXTBSY 容错：cargo 并发写 build-script 后立即 exec 偶发 `Text file busy (os error 26)`（真机预检第一轮实测命中一次，重跑即过）；build() 与 cargo test 均失败重试一次，genuine 编译错误第二轮照常抛出
- release profile 沿用上游：`lto=true, opt-level="z", codegen-units=1, panic="abort"`

## 测试（真机预检已实测，CI 复跑同样口径）

- 上游测试：`cargo test --release --lib --bins`，在 test_package 阶段执行（hmbs 预检只从 test_package 阶段 stdout 采集 `HMBS_UPSTREAM_TEST_RESULT` 标记，tlsx/1.2.2 先例）
- **单元 41 个执行全部真实通过**（真机实测 cargo 两条 result 行：lib `18 passed` + bin `23 passed`，合计 41 执行 41 通过；src 侧唯一 #[test] 23 个：src/config.rs 16 + src/generator.rs 2 + src/main.rs 5（clap 解析），bin 目标重复纳入 lib 模块 18 个）
- **集成 12 个 NOT_RUN**（tests/test_cases.rs：test_01…test_11 + test_07a，无任何 #[cfg] 条件门；fixture 树单元生成 diff），双重独立原因：
  1. 编译层：dev-dep nix 0.23 pre-ohos cfg 缺陷（见补丁说明），上游范围无兼容版本——平台适配阻塞，具体报错定位见 MANIFEST.yml 审计；
  2. 运行层：其 `#[ctor] unshorn()` 在非 root 且 unshare(NEWUSER) 被拒时打印 "skipping tests" 并 exit(0)——本设备 SSH 非 root、内核禁 user namespace，即使可编译也是 0 执行。
- **官方总量口径 53 个**（41 cargo result 行 + 12 集成函数；唯一 #[test] 函数 35 = src 23 + tests/ 12），真实通过率 **41/53（77.4%）**
- doc-tests 排除：OHOS harmonybrew 工具链无 rustdoc（真机探针实证，DRAFT-rust-toolchain-no-rustdoc-skip-doctests / martin、argc 等已合入先例），`--lib --bins` 天然不含该阶段
- 消费者冒烟 test.sh 4 例（真机预检全部通过）：
  1. `--version` 输出 "zram-generator 1.2.1"（musl/OHOS 二进制端到端可执行）
  2. `--help` 含 `--setup-device` 与编译期内联文本 `Uses /usr/lib/systemd/systemd-makefs`（证明 make 变量覆盖构建路径生效）
  3. 生成器模式：`ZRAM_GENERATOR_ROOT` 指向临时根 + `[zram0]` 配置 → 产出 `dev-zram0.swap`（391MB = mem/2，What=/dev/zram0）——OHOS 独立 CLI 交付形态；rust-ini/liboverdrop/fasteval 路径真机执行
  4. 无内核 zram 时 `--setup-device zram0` 干净报错（exit 1，anyhow 上下文，无 panic）——OHOS 缺内核特性的行为断言

## 已知限制

- 设备内核无 zram（`/sys/class/zram-control`、`/dev/zram*` 不存在，/proc/modules 无 zram）：真实 mkswap/swapon 路径无法真机验证；systemd-makefs 在 OHOS 也不存在
- SELinux 拒绝读 `/proc/swaps`、`/sys/class/block`：设备上 swap 状态观测面受限
- 上游无 systemd 拉起形态：OHOS 上 `systemd-zram-setup@.service` 不交付；开机自动化需其他 init 机制对接（不在本 run 范围）
- 设备侧注意事项：工作期间曾观察到一次 `$HOME` 下工作目录内容丢失事件，与目录命名（含 "tmp" 字样）的因果关系未获证实（现场复核 ~/.tmp-zram-dl、~/tmp 等含 tmp 字样目录均长期完好存活）；构建/预检目录避开 "tmp" 命名属零成本规避，仍建议采纳
