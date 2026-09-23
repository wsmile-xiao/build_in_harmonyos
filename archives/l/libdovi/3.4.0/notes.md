# libdovi 3.4.0 适配笔记

## 编译环境
- 构建系统: custom（Rust cargo + cargo-c）
- 编译日期: 2026-09-18
- 编译器: clang/clang++（Conan tools.build:compiler_executables）
- 状态: built（待真机预检确认）

## 上游信息
- 名称: libdovi（Rust crate 名 dolby_vision）
- 版本: 3.4.0
- 仓库: https://github.com/quietvoid/dovi_tool/tree/main/dolby_vision
- 归档: https://github.com/quietvoid/dovi_tool/archive/refs/tags/libdovi-3.4.0.tar.gz
- 校验: sha256 8eac4d1c3134f53e8eb216db6450307a737425844113e480d1e9713c142a9fa2
- 许可: MIT
- 最低 Rust: 1.88.0（Harmonybrew 瓶内 Rust 1.98.1 满足）

## 编译步骤

归档解包后源码树根含 `dolby_vision/` 与 `assets/`，以下均在 `dolby_vision/` 内执行：

```bash
# 1. Rust 工具链（复用 bulletty/0.2.2 验证过的 Harmonybrew 兜底）
#    缺 cargo/rustc 时从 conandata.yml rust_toolchain 下载解包，
#    并用 rsproxy.cn 注册表加速 crates.io
# 2. cargo-c（提供 cargo cbuild/cinstall）
cargo cbuild --version || cargo install cargo-c --locked
# 3. 上游测试（配方 build() 内自动执行，失败即阻断）
cargo test --release --locked --all-features
# 4. 构建 C 库（shared=False 走 staticlib，shared=True 走 cdylib）
cargo cbuild --release --locked --all-features --library-type=staticlib --prefix=/
# 5. 安装到 Conan 包目录
cargo cinstall --release --locked --all-features --library-type=staticlib --prefix=/ --destdir=<package_folder>
```

OHOS 下自动追加 `--target aarch64-unknown-linux-ohos`，linker 取 Conan 的 clang。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 真机可能缺 cargo/rustc/cargo-c | OHOS 镜像未预装 Rust | 配方自动探测，缺失时解包 Harmonybrew Rust 瓶并 `cargo install cargo-c --locked` |
| 2 | crates.io 直连慢/不稳 | CI 网络限制 | 在 `dolby_vision/.cargo/config.toml` 写入 rsproxy-sparse 替换源，重试 10 次 |
| 3 | 归档根不是 crate 根 | dovi_tool 仓库归档含多顶层目录 | `strip_root=True` 后进入 `dolby_vision/` 子目录构建 |
| 4 | 头文件路径不直观 | cargo-c 按 `cbindgen.toml` 生成 `include/libdovi/rpu_parser.h` | test.c 用 `__has_include` 兼容 `<libdovi/rpu_parser.h>` 与 `rpu_parser.h`，编译时同时加 `-Iinclude` |

## 源码修改

无补丁。`patches_applied: []`。

## 依赖版本

- Rust 1.98.1（Harmonybrew 瓶，满足 >=1.88.0）
- cargo-c（真机按需 `cargo install cargo-c --locked`）
- 其余 Rust 依赖由 `dolby_vision/Cargo.lock --locked` 锁定，经 rsproxy 获取

## 验证结果

待 HMBS 真机预检回填：

```bash
# 配方内上游测试
cargo test --release --locked --all-features
# 消费者测试（test_package）
./test_libdovi
```

- 上游测试输出以 `HMBS_UPSTREAM_TEST_RESULT` 标记为准（framework=cargo-test）
- 消费者测试输出以 `HMBS_TEST_PACKAGE_RESULT` 标记为准（discovered=5/passedCount=5）

## 交付物

| 文件 | 说明 |
|------|------|
| include/libdovi/rpu_parser.h | C-API 头文件 |
| lib/libdovi.a（或 libdovi.so） | 静态库（默认）/共享库（-o shared=True） |
| lib/pkgconfig/dovi.pc | pkg-config 描述（cargo-c 生成） |
| licenses/LICENSE | 上游 MIT 许可 |

## 注意事项

- 默认 `shared=False` 产出静态库，避免 .so 污染；需要共享库可用 `-o libdovi/*:shared=True`。
- `cargo test` 必须在真机完整执行，不得跳过；数字以实际 `test result:` 行解析为准。
- 本机未运行 conan，一切结论以真机预检日志为准。

## 2026-09-19 真机中断修复（未提交，待预检）

- 现象：预检在 `cargo install cargo-c --locked` 编译 `gix-filter` 时 SSH 中断（`Connection closed`），另有 `preflight.sh: can't create /tmp/... Read-only file system`（readonly_tmp）。
- 根因：每次构建都从源码编译 cargo-c（约 200 个 crate，jobs=1 下耗时过长），且 cargo 临时/目标目录未全部约束到可写目录。
- 修复：新增 `conandata.yml cargo_c` 官方预编译 musl 二进制（v0.10.0，aarch64/x86_64，sha256 已实测），`_ensure_cargo_c` 优先下载解包验证直用，仅回退才源码安装；`_cargo_env` 改用 `_pick_writable_tmpdir` 探针并统一 `CARGO_HOME`/`CARGO_TARGET_DIR` 到 build 目录；源码安装追加 `--target-dir` 到可写目录。

## 2026-09-19 第二轮修复（与首轮不同策略，未提交，待预检）

- 前次：新增官方 musl 预编译 cargo-c 快速通道并收紧 CARGO_HOME/CARGO_TARGET_DIR。
- 本轮差异：彻底删除 `cargo install cargo-c --locked` 源码回退链（约 200 个 crate，真机编译 gix-filter 时 SSH 中断的直接凶手），不再保留该杀手路径。
- 新回退链：预编译 cargo-c 不可用时走免 cargo-c 手动构建——`cargo rustc --crate-type=staticlib/cdylib -- --cfg cargo_c`（上游 src/lib.rs 以 `cfg(any(cargo_c, feature=capi))` 门控 C API，--all-features 下符号齐全，已核对 capi.rs 的 7 个被测符号）+ 轻量 `cargo install cbindgen`（约 20 个 crate）生成头文件 + 手写 dovi.pc，产物布局与 cargo-c 一致（include/libdovi/rpu_parser.h、lib/libdovi.a(.so)、lib/pkgconfig/dovi.pc）。
- 只读 /tmp：手动构建沿用同一可写 build 目录（CARGO_HOME/CARGO_TARGET_DIR/TMPDIR 探针），不新增 /tmp 写入点。
