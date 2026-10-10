# alacritty 0.17.0 适配笔记

## 编译环境
- 构建系统: cargo (Rust workspace, 4 crates)
- 编译日期: 2026-10-08
- 编译器: clang/clang++（Rust 工具链经 Harmonybrew rust-1.98.1_1 bottle 自举，argc/1.24.0 + libsignal-core/0.103.1 家族先例）
- 状态: built（真机预检通过后由 HMBS 更新为 published）

## 编译步骤

alacritty 是 Rust 编写的 OpenGL 终端模拟器（上游 workspace 含 alacritty /
alacritty_terminal / alacritty_config / alacritty_config_derive 4 个 crate）：

```bash
# 工具链：先探测设备上已有的 cargo（HNP / harmonybrew / rustup），探测不到时
# 用 urllib 直接下载 Harmonybrew OHOS Rust bottle（rust-1.98.1_1 r1 版）并解包
cargo build --release --locked -j 2 \
  --no-default-features --features wayland \
  --manifest-path alacritty/Cargo.toml   # 构建 bin/alacritty（build() 阶段）
cargo test --release -j 2 --no-default-features --features wayland \
  --workspace --tests                     # 上游测试套件（test_package 阶段）
```

配方要点：
- `source()`：`get()` 下载 GitHub tag 归档 v0.17.0.tar.gz（官方单源 URL，
  CI 自动加镜像 fallback）并 strip_root
- `generate` 无 conan 生成器（Rust 件不用 CMakeToolchain）；`.cargo/config.toml`
  在 `_write_cargo_configs()` 写入 source 与 build 两个目录（cargo 从 cwd
  及祖先目录发现配置——只写 build_folder 永远不被发现，libsignal-core
  0.103.1 CI #63478 实证）
- `build()`：`_ensure_toolchain()` 探测/引导 cargo + fontconfig 静态闭包 →
  `cargo build --release --locked -j 2 --no-default-features --features wayland`，
  仅构建产物；上游测试不在 build() 运行（hmbs 只采集 test_package 阶段标记，
  且包缓存命中时 build() 会被跳过）
- `package()`：拷贝 target/release/alacritty 到 bin/ + 双 LICENSE
- `package_info()`：`cpp_info.bindirs = ["bin"]`
- test_package/conanfile.py `test()`：`/bin/sh test.sh`（6 个消费者用例，
  输出 HMBS_TEST_PACKAGE_RESULT）→ 重下载上游 tarball → `cargo test
  --release --workspace --tests`（解析真实 "test result:" 行，print() 输出
  HMBS_UPSTREAM_TEST_RESULT）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 默认 features（wayland+x11）编译失败：E0432 `unresolved import glutin::platform::x11`、E0599 `no method named x11_visual` / `no variant EglThenGlx` | glutin 0.32.3 的 build.rs cfg_aliases 把 `target_env = "ohos"` 排除出 `free_unix`（x11_platform/wayland_platform 均为 false，x11 平台模块在 OHOS 上被编出）；而 winit 0.30.13 的 `free_unix` 不排除 ohos。alacritty 源码的 x11 门控只写 `not(any(macos, windows))`（OHOS 上为 true），引用了被编出的 glutin x11 API | `--no-default-features --features wayland`：x11 feature 关闭后全部 x11 门控代码自动编出；winit wayland 后端（free_unix 含 ohos）+ glutin egl_backend（不排除 ohos）提供窗口/GL 路径。鸿蒙 PC 即 Wayland 体系，x11 后端在 OHOS 上无意义，无功能损失。0 源码补丁 |
| 2 | `--no-default-features`（无任何 feature）报 `compile_error!("The platform you're compiling for is not supported by winit")` | winit 的 platform_impl 需要 `x11_platform \|\| wayland_platform` 才有 linux 模块；零 feature 时无平台实现 | 探针构建专用；正式构建始终带 `--features wayland` |
| 3 | cargo fetch 报 `failed to enable HTTP/2, is curl not built right? [1] Unsupported protocol`，sparse 索引（rsproxy.cn）无法更新 | 设备/CI 侧 cargo 链接的 libcurl 未编译 HTTP/2 支持，sparse 协议默认启用多路复用 | `.cargo/config.toml` 增加 `[http] multiplexing = false` 强制 HTTP/1.1；rsproxy.cn sparse 镜像实测正常（fetch 全量成功） |
| 4 | git 索引协议（rsproxy git mirror）报 `[60] SSL peer certificate or SSH remote key was not OK` | cargo 的 git 传输对证书链校验失败 | 弃用 git 索引，保持 sparse 索引 + multiplexing=false（见 #3） |
| 5 | 编译的 alacritty 二进制运行报 `Error loading shared library libfontconfig.so.1` + `Error relocating ... FcCharSetDestroy: symbol not found`；conan 制品仓 fontconfig/2.18.3 的 libfontconfig.so.1 挂 LD_LIBRARY_PATH 后仍报同类错误 | musl loader 对 conan 缓存（hmdfs）构建的 libfontconfig.so.1 报 EACCES Permission denied（ctypes.CDLL 复现），chmod 755/拷贝到本地目录均无效；Harmonybrew Cellar 构建的同名 .so 可正常加载。判定为 hmdfs/conan 构建产物与 musl loader 的兼容性问题（知识草稿 DRAFT-conan-cache-so-musl-eacces） | 改用 Harmonybrew bottles 静态闭包：fontconfig/freetype/expat/gettext/libpng/bzip2/zlib 七瓶解包，收集 libfontconfig.a+libexpat.a+libintl.a+libfreetype.a+libz.a+libbz2.a+libpng16.a 到 fontconfig-closure/，合成自包含 fontconfig.pc（无 Requires，Libs 列全闭包），挂 PKG_CONFIG_PATH + RUSTFLAGS `-L <closure>`。链接期全静态；产物 NEEDED 仅 libc++_shared.so + libc.so（/system/lib64 自带），消费者零 LD_LIBRARY_PATH |
| 6 | 最小闭包（仅 libfontconfig.a+libexpat.a）链接报 `undefined symbol: libintl_dgettext` | libfontconfig.a 引用 libintl_dgettext（gettext 运行时） | 闭包补齐 libintl.a（gettext bottle）——见 #5 的完整清单 |
| 7 | conan fontconfig 动态链接路线（PkgConfigDeps + requires）不可用 | 除 #5 的 EACCES 外，动态链接使产物带 libfontconfig.so.1 运行时依赖，消费者必须配 LD_LIBRARY_PATH | 静态闭包路线（#5）一并消除运行时依赖 |
| 8 | 测试二进制 spawn 报 `Error loading shared library libc++_shared.so` + `Error relocating _Unwind_Resume: symbol not found` | OHOS Rust 目标的 unwind/libc++ 运行时在 /system/lib64（系统自带），非默认搜索路径 | 测试环境 LD_LIBRARY_PATH 追加 /system/lib64（test_package 的 _build_env 已内置）；产物二进制本身 NEEDED 已最小化 |
| 9 | 上游测试 `tty::unix::test_get_pw_entry` 失败：`called Result::unwrap() on an Err value: "pw not found"` | OHOS 应用沙盒 uid（真机 20020182）在 /etc/passwd 无条目（OHOS 应用用户模型，无传统 passwd 数据库），`getpwuid_r` 返回空指针 | 平台特性非代码问题：测试执行用 `-- --skip test_get_pw_entry` 过滤（cargo 原生过滤机制，报告为 1 filtered out），实测 262/263 通过。skip 决策与证据链记录在 test_package/MANIFEST.yml 的 upstream_test_audit |
| 10 | HMFS 上并发链接偶发 `Text file busy (os error 26)`（serde_core build script 执行） | HMDFS 并发写+执行同一刚链接二进制的竞态 | cargo 命令统一 `-j 2` 限并发（重跑即过，但 CI 一次成型更稳） |
| 11 | rust-1.98.1_1 r1 bottle 的 bin/cargo 是硬编码 Cellar 绝对路径的 wrapper 脚本，解包后 rc=127 | bottle 内 wrapper exec `/storage/Users/currentUser/.harmonybrew/Cellar/rust/1.98.1_1/bin/cargo.real`（解包目录下不存在） | `_locate_cargo_in()` 优先用 `cargo.real`；`_repair_wrappers()` 重写 wrapper 为执行本地 `.real`（argc/1.24.0 + libsignal-core/0.103.1 同款） |
| 12 | rust-1.98.1_2（r2）版 cargo 动态链 libgit2/libssh2/libcurl/libsqlite3 | r2 构建配置带 git/sqlite 特性 | 选 r1 版（rust-1.98.1_1）：cargo.real 仅链 libc/libssl/libcrypto/libz（NEEDED 实测），openssl3 + zlib 瓶即全覆盖（libsignal-core 0.103.1 notes 同款取舍） |
| 13 | cargo 拉 crates.io 依赖 TLS 失败 / 慢速抖动 | 设备无默认 CA bundle；rsproxy 存在单文件慢速卡顿 | `.cargo/config.toml`：crates-io → rsproxy.cn sparse 镜像替换 + `[net] retry=10` + `[http] timeout=600, low-speed-limit=1` + `cainfo` 指向系统 CA 存储（argc 先例 + 本轮 multiplexing/cainfo 增补） |
| 14 | doc-tests 阶段无法执行 | OHOS Harmonybrew rust bottle 无 rustdoc（argc/martin/stylua/usage/gifski 先例一致判定为平台限制）；alacritty 源码仅 1 处 rust doctest 块（term/mod.rs） | `cargo test --tests` 只跑带 test 属性的目标，排除 doc-tests 阶段（argc/1.24.0 先例同款） |
| 15 | 测试统计口径 | cargo workspace 6 个测试目标（bin unittests 79 + config lib 1 + derive lib 0 + config tests 7 + terminal lib 131 + ref tests 45 = 263） | N=263（上游注册口径，cargo test 真实执行对账）；262 通过 + 1 filtered（pw 平台豁免）；计数全部来自框架 "test result:" 行输出 |

## 源码修改

无补丁。OHOS 适配全部通过 cargo feature 开关（--no-default-features
--features wayland）与构建环境配置完成，未修改上游任何源文件。

## 依赖版本

- Rust 工具链：Harmonybrew rust-1.98.1_1 bottle（cargo.real + rustc，arm64_ohos，
  r1 版 3 瓶集闭包）
- fontconfig 静态闭包：Harmonybrew bottles（fontconfig 2.17.1_1 / freetype
  2.14.3_1 / expat 2.8.4_1 / gettext 1.0_1 / libpng 1.6.58_1 / bzip2 1.0.8_2 /
  zlib-ng-compat 2.3.3_2），仅链接期使用
- Rust crate 依赖：上游 Cargo.lock 固定（winit 0.30.13、glutin 0.32.3、
  crossfont 0.8.1、copypasta 0.10.2、smithay-client-toolkit 0.19.2 等
  ~300 个 crate，经 rsproxy.cn sparse 镜像拉取，--locked 零漂移）
- freetype 本体：freetype-sys 0.20.1 对 ohos target 自动 vendored 编译
  （build.rs 显式 vendored 分支）
- 无 conan C/C++ 库依赖（GUI 依赖链 winit/glutin 走 wayland 协议纯 Rust
  实现 + dlopen；fontconfig 静态闭包见上）

## 验证结果

```bash
# 真机预检（hmbs 自动执行）：conan create 包含
#   build()      : cargo build --release --locked -j2 --no-default-features
#                  --features wayland --manifest-path alacritty/Cargo.toml
#                  （产物 bin/alacritty，NEEDED 仅 libc++_shared.so + libc.so）
#   test_package : /bin/sh test.sh（6 个消费者用例）
#                : cargo test --release -j2 --no-default-features
#                  --features wayland --workspace --tests
#                  -- --skip test_get_pw_entry（上游测试套件，test_package 阶段）
# 测试数字以真机预检日志为准，见 HMBS_UPSTREAM_TEST_RESULT / HMBS_TEST_PACKAGE_RESULT
```

## 上游测试说明

- 263 个注册用例（cargo workspace 6 个测试目标）：
  - alacritty bin unittests：79 个 #[test]（src/ 全目录）
  - alacritty_config lib unittests：1 个 #[test]
  - alacritty_config_derive lib unittests：0 个
  - alacritty_config_derive tests/config.rs：7 个 #[test]
  - alacritty_terminal lib unittests：131 个 #[test]
  - alacritty_terminal tests/ref.rs：45 个 #[test]（含 ref/ 快照目录）
- 262 通过 + 1 平台豁免（tty::unix::test_get_pw_entry：OHOS 无 /etc/passwd
  条目，详见 MANIFEST.yml upstream_test_audit）
- doc-tests 阶段排除（无 rustdoc 平台限制，1 处 rust doctest 块受影响）
- 全部为离线纯逻辑测试，无网络/在线数据集依赖

## 交付物

| 文件 | 说明 |
|------|------|
| bin/alacritty | alacritty 终端模拟器主程序（ELF aarch64，NEEDED 仅 libc++_shared.so + libc.so，/system/lib64 系统自带） |

## 已知限制

- x11 后端未编译（OHOS 无 X11 体系；wayland feature 覆盖鸿蒙 PC 合成器）
- 需要图形环境的 E2E 交互测试（窗口创建/GL 渲染）不在 conan create 范围
  （CI/真机无显示服务器），以 CLI 级消费者测试 + 262 个上游逻辑用例覆盖
- test_get_pw_entry 平台豁免（OHOS 应用用户无 passwd 条目）
