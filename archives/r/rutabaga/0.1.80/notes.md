# rutabaga 0.1.80 适配笔记

## 0. 目标库识别

| 项 | 值 |
|---|---|
| 任务名 | `rutabaga`（分支 `feat/rutabaga-0.1.80`） |
| 真实上游 crate | **`rutabaga_gfx` 0.1.80**（crates.io） |
| 上游仓库 | https://github.com/magma-gpu/rutabaga_gfx （tag `v0.1.80`，git sha1 `d1b06416e2353c99c99e61eab15560484f45496f`） |
| 许可证 | BSD-3-Clause |
| 语言 / 构建系统 | 纯 **Rust**（edition 2021，MSRV 1.81.0）/ **cargo** |
| 产物 | `librutabaga_gfx.rlib`（Rust 静态库；`has_lib=true`、`bin_names=[]`、无 C API） |
| 源码 sha256 | `2817d168222af3c49269f583dd8e67429912953ae608f715fd97683ed50320a5`（与 crates.io registry checksum 逐字一致） |

`Rutabaga Virtual Graphics Interface (VGI)` 是跨平台 GPU/显示半虚拟化抽象，被 VMM
（crosvm 等）以 Rust 依赖方式消费。发行版层面无同名独立包（Fedora 的
`rutabaga-gfx-ffi` 是同家族 FFI 包；crates.io 无 `rutabaga`；PyPI `rutabaga 0.0.2`
为同名异物）。

## 1. 依赖（W0）

| 依赖 | 版本 | 类型 | 核验 |
|---|---|---|---|
| `rust-toolchain` | 1.97.1 | tool_requires（构建工具链） | `conan download rust-toolchain/1.97.1 -r=ohpcd --only-recipe` → EXIT=0 |
| 9 条必选 crate（`cfg-if`/`libc`/`log`/`remain`/`serde`/`serde_json`/`thiserror`/`zerocopy`/`magma-gpu`）+ 可选 `vulkano` + build-dep `pkg-config` + 82 个传递 crate | — | cargo 从 crates.io（rsproxy 镜像）拉取 | 非 conan 包，不作为依赖适配 |

默认 features 为空：`build.rs` 不 probe 任何 C 库，`Cargo.lock` 闭包无第三方 `-sys`
crate ⇒ 默认构建**不链接任何外部 C/C++ 第三方库**。可选后端
（`gfxstream` / `virgl_renderer` / `gbm`）默认不启用，未计入强制依赖。

## 2. OHOS 平台适配（必做，均为真机实测）

1. **Rust 工具链**：`tool_requires("rust-toolchain/1.97.1")`（rustup 不识别 HarmonyOS
   宿主，报 `unrecognized OS type: HarmonyOS`）。
2. **ELF 签名**：该工具链包内 ELF 无 HarmonyOS 代码签名，OHOS loader 直接拒绝
   （`Permission denied (os error 13)`）。`cargo`/`rustc` 及 `librustc_driver*.so`、
   cargo 运行期 OpenSSL/zlib 均复制到 build folder 后 `binary-sign-tool -selfSign 1`
   自签。
3. **rustlib 必须是真实目录**：`lib/rustlib` 若为符号链接，rustc 找不到
   `aarch64-unknown-linux-ohos` 的 `std`/`core`，报 `E0463 can't find crate for std`。
   配方用 `copytree` 实体复制。
4. **OpenSSL ≥ 3.5**：cargo 1.97 动态链 `libssl.so`，需要 `SSL_get0_group_name`
   （`OPENSSL_3.2.0` 版本符号）；设备镜像自带 `libssl.so.3` 无该符号 →
   `symbol not found`。改用 Harmonybrew `openssl@3-3.6.4` OHOS bottle
   （与 `libetebase`/`below` 同源），`libz` 取 `zlib-ng-compat-2.3.3_1` bottle，
   签名后入 `LD_LIBRARY_PATH`。
5. **链接器**：SDK 的 `aarch64-unknown-linux-ohos-clang` 是 `/bin/sh` 包装脚本，
   rustc exec 该脚本报 `Permission denied`；改为直接调用 `clang-15` ELF，并注入
   `--target aarch64-linux-ohos --sysroot=<sdk>/native/sysroot -D__MUSL__`。
6. **/tmp 只读**（E002）：`TMPDIR`/`TMP`/`TEMP` 重定向到 build folder 内可写目录。
7. **crate 拉取**：`rsproxy.cn` sparse 镜像 + 显式 CA。CA 按候选列表探测
   （`SSL_CERT_FILE`/`CURL_CA_BUNDLE` → `/storage/Users/currentUser/usr/local/ssl/cert.pem`
   → `/etc/ssl/certs/cacert.pem` → `/etc/ssl/cert.pem`），并同时写入环境变量
   `SSL_CERT_FILE`/`CURL_CA_BUNDLE`/`CARGO_HTTP_CAINFO` 与 cargo `[http] cainfo`。
   **主 recipe 与 test_package 必须使用同一候选列表**：CI Worker 上没有
   `/storage/Users/currentUser/usr/local/ssl/cert.pem`，但有 `/etc/ssl/certs/cacert.pem`；
   若 test_package 漏掉后者，cargo 更新索引会失败
   （`download of config.json failed: self-signed certificate in certificate chain (19)`），
   而主 recipe 因回退到该 CA 而正常——此处曾造成一次 CI 红。

> 以上 1-7 全部落在 `conanfile.py` 内自管，不依赖任何未发布依赖（W0/R36 通过）。

## 3. 构建与测试

```bash
# 真实构建
cargo build --release --target aarch64-unknown-linux-ohos
# → Finished `release` profile [optimized]，产出 target/aarch64-unknown-linux-ohos/release/librutabaga_gfx.rlib

# 上游测试（crate 注册 8 个 #[test]，autotests=false 无集成测试目标）
cargo test --release --lib --target aarch64-unknown-linux-ohos
# → test result: ok. 8 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out
```

上游测试用例（逐项）：

| # | 用例 | 模块 |
|---|---|---|
| 1 | `rutabaga_core::tests::snapshot_restore_2d_no_resources` | src/rutabaga_core.rs |
| 2 | `rutabaga_core::tests::snapshot_restore_2d_one_resource` | src/rutabaga_core.rs |
| 3 | `rutabaga_gralloc::formats::tests::format_debug` | src/rutabaga_gralloc/formats.rs |
| 4 | `rutabaga_gralloc::formats::tests::canonical_formats` | src/rutabaga_gralloc/formats.rs |
| 5 | `rutabaga_gralloc::formats::tests::canonical_planar_formats` | src/rutabaga_gralloc/formats.rs |
| 6 | `rutabaga_gralloc::gralloc::tests::create_render_target` | src/rutabaga_gralloc/gralloc.rs |
| 7 | `rutabaga_gralloc::gralloc::tests::create_video_buffer` | src/rutabaga_gralloc/gralloc.rs |
| 8 | `rutabaga_gralloc::gralloc::tests::export_and_map` | src/rutabaga_gralloc/gralloc.rs |

> `cargo test`（不加 `--lib`）会额外触发 doc-test 阶段，而 `rust-toolchain/1.97.1`
> 包内**不含 `rustdoc`**，故采用 `--lib` 精确覆盖上游单元测试目标（本 crate 无
> doctest，`--lib` 与完整单元测试集合一致）。

## 4. 首个真实错误 → 根因 → 修复（时间线）

| # | 首个错误 | 根因 | 最小修复 |
|---|---|---|---|
| 1 | `Permission denied (os error 13)` 执行 cargo/rustc | 未签名 ELF 被 OHOS loader 拒绝 | `binary-sign-tool -selfSign 1` 自签 |
| 2 | `Error loading shared library libssl.so` | 运行库未签名/未就位 | 复制并签名 cargo 运行期库 |
| 3 | `SSL_get0_group_name: symbol not found` | 设备自带 OpenSSL 过旧 | 改用 harmonybrew openssl@3-3.6.4 |
| 4 | `E0463 can't find crate for std` | `lib/rustlib` 为符号链接 | `copytree` 实体复制 rustlib |
| 5 | `could not exec the linker ... Permission denied` | SDK clang 包装脚本无法作为 rustc linker | 直接调用 `clang-15` ELF + link-arg（`--target/--sysroot/-D__MUSL__`） |
| 6 | `error: doctest failed … rustdoc` | 工具链包不含 `rustdoc` | `cargo test --lib`（上游单元测试目标） |
| 7 | `Package type is 'library', but no 'shared' option declared` | conan 对 library 包的强制要求 | 声明 `options={"shared":[True,False]}`，`default_options shared=False`，并在 `configure()` 拒绝 shared=True |
| 8 | `BadZipFile: File is not a zip file` | crates.io 下载端点无扩展名，`get()` 误判为 zip | `source()` 用 `download()` 存为 `.tar.gz` + `tarfile` 解包 + strip root |
| 9 | `NotFoundException: zlib-ng-compat-2.3.3_1…bottle` | 旧配方引用的 Harmonybrew zlib bottle 已下线（404） | 改用平台自带 `/system/lib64/platformsdk` 的 `libz.so`（加入 LD_LIBRARY_PATH） |
| 10 | `ld.lld: error: cannot open Scrt1.o / unable to find library -lc` | conan profile 的 `tools.build:compiler_executables.c` 指向 `/data/service/hnp/bin/clang` 包装脚本，其推导 sysroot 错误 | `_ohos_clang()` 优先按 SDK 布局 glob `clang-15`，profile conf 仅作定位 |
| 11 | `Text file busy (os error 26)`（偶发） | HMDFS 上新写入的 build script 立即 exec | cargo 调用加 3 次 ETXTBSY 重试 |

## 5. 鸿蒙特有验证

`test_package/consumer.rs` 内含鸿蒙特有断言：
- 运行目标必须是 `aarch64-unknown-linux-ohos`（`target_env = "ohos"`）；
- 用设备可写的 `TMPDIR`（`std::env::temp_dir()`，鸿蒙 `/tmp` 只读）做
  `Rutabaga::snapshot()` / `restore()` 往返，命中鸿蒙只读 `/tmp` 适配点。

test_package 断言数 = 4（其中鸿蒙特有 2）；上游 `cargo test` 实测 8/8。

## 6. W3 本地 CI 模拟的环境前提（框架侧注意事项）

设备 `/tmp` 为只读（E002）。框架 W3 通过 `zsh ci/conan/build_and_test.sh` 运行
CI 脚本，而该 zsh（5.9, aarch64-unknown-linux-ohos）**here-document 临时文件不读取
`TMPDIR`，固定走 `/tmp`**（`can't create temp file for here document: read-only file
system`），导致 L0i/L0m 等含 here-doc 的检查直接失败。解决：导出
`TMPPREFIX=<可写目录>/zsh`（zsh 的临时文件前缀）后再运行 W3，即全部通过。

另：W3 以全仓（full）模式扫描时，JC 会命中本仓库其它包的历史遗留隐藏文件
（`archives/c/cloog/0.21.1/.build-closed`、`.staging-verified` 等 5 个），与本包无关；
按真实 CI 的 PR 差异模式（`JUNK_PR_DIFF=<pr.diff>`）运行后 JC 通过。
---

**编译结束**: 2026-10-01 16:59
**最终状态**: built
