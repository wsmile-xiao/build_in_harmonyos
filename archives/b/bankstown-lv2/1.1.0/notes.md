# bankstown-lv2 1.1.0 适配笔记

## 编译环境
- 构建系统: cargo (Rust cdylib)
- 编译日期: 2026-08-29
- 编译器: clang/clang++（OHOS Rust target: aarch64-unknown-linux-ohos）
- 状态: built

## 编译步骤

1. 下载上游 tarball（gh-proxy.com 镜像 → GitHub 官方兜底，sha256
   `e877508b...734675`，conandata.yml）。
2. 探测/引导 Rust 工具链：先找 HNP/harmonybrew/rustup 的 cargo；没有则用
   urllib 下载 Harmonybrew OHOS rust bottle（rust-1.97.1 + openssl@3 + zlib-ng）
   解包到 build 目录（argc/at51/martin 先例）。
3. `generate()` 写 `.cargo/config.toml`：clang 链接器 + rsproxy.cn sparse 镜像
   + 网络容错（retry=10, timeout=600, low-speed-limit=1）。
4. `_apply_lv2_sys_patch()`：下载 lv2-sys-2.0.0 crate（rsproxy），校验 sha256
   （与 crates.io 官方一致），解包到 build/vendor/lv2-sys，给 src/lib.rs 追加
   `#[cfg_attr(target_os = "ohos", path = "linux/mod.rs")]`，并把
   `[patch.crates-io] lv2-sys = { path = ... }` 追加进 `.cargo/config.toml`。
5. `cargo build --release`（cwd=source_folder）。注意：不能加 `--locked`——
   Cargo [patch] 会更新 Cargo.lock 中 lv2-sys 的 source 记录，--locked 会拒绝。
6. 产物 libbankstown.so + bankstown.ttl + manifest.ttl 装入
   lib/lv2/bankstown.lv2/ 形成 LV2 bundle。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | lv2-sys 2.0.0 在 OHOS 编译报 `compile_error!("The targeted operation system is not supported by rust-lv2!")` | rust-lv2 的 FFI crate 用 `#[cfg(target_os = "linux")]` / `"windows"` 选择预生成绑定模块；OHOS target 报 `target_os = "ohos"`，落入 unsupported.rs | 该 crate 的 `src/linux/aarch64.rs` 是纯类型/常量绑定（无 libc 依赖、无 build.rs），在 vendor 副本的 lib.rs 给 linux 与 ohos 都 cfg-attr 到 linux 模块；用 Cargo `[patch.crates-io]` 覆盖 Cargo.lock 固定版本 |
| 2 | cargo 直连 crates.io TLS 失败 | worker 无 crates.io CA bundle | 改用 rsproxy.cn sparse 镜像（argc 先例），有系统 CA 时设 SSL_CERT_FILE |
| 3 | OHOS /tmp 只读且常满 | 平台限制 | 构建/测试用可写 TMPDIR（~/tmp/bankstown-lv2） |
| 4 | 设备无 CA bundle，urllib 下载 harmonybrew/rsproxy 失败 | 设备 Python 无默认 CA store | SSL_CERT_FILE 指向系统 CA（usr/local/ssl/cert.pem 等）；全无时对固定内部镜像用未验证 TLS context（argc/at51 先例） |
| 5 | OHOS 无 cc 符号链接 | 平台限制 | RUSTFLAGS `-C linker=clang`；OHOS SDK sysroot 存在时加 `-C link-arg=-Wl,--code-sign`（at51 先例：真机 dlopen/加载需要 code-sign） |

## 源码修改

无对上游源码树的修改。唯一补丁是对 vendor 的 lv2-sys-2.0.0 crate 就地追加一行
cfg-attr（见 conanfile.py `_apply_lv2_sys_patch`），通过 Cargo `[patch]` 生效，
不改 Cargo.toml/Cargo.lock/上游任何文件。

## 依赖版本

- Rust 工具链: 1.97.1 (Harmonybrew OHOS bottle: rust + openssl@3 + zlib-ng-compat)
- crate 依赖 (Cargo.lock 固定):
  - lv2 0.6.0（lv2-core 3.0.0 / lv2-sys 2.0.0 / lv2-atom 2.0.0 / lv2-urid 2.1.0 / urid 0.1.0 / lv2-midi 1.2.0 / lv2-units 0.1.3 / wmidi 3.1.0）
  - biquad 0.4.2（含 libm 0.1.4）
  - 构建期: proc-macro2 1.0.69 / quote 1.0.33 / syn 1.0.109 / unicode-ident 1.0.12 / lv2-core-derive 2.1.1 / urid-derive 0.1.1

## 验证结果

在 HarmonyOS aarch64 真机预检环境执行：

```bash
# conan create（build + test_package）
conan create . --profile=ohos   # 或经 hmbs 预检流水线

# test_package 内两段验证：
# 1) 真实 C 消费者（dlopen + LV2 C API 生命周期）
clang -O1 src/test_bankstown_lv2.c -ldl && ./test_bankstown_lv2 <bundle>
#    → dlopen(lib/lv2/bankstown.lv2/bankstown.so) 成功
#    → lv2_descriptor(0) 非空，URI=https://chadmed.au/bankstown
#    → instantiate(48kHz) → connect_port 12 端口 → activate → run(64) 输出非零
#    → bypass=1 输入直通 → deactivate → cleanup → dlclose
# 2) 上游测试审计（test_audit.py 重新下载上游 tarball 扫描）
python3 test_audit.py <bundle> <workdir>
#    → 确认上游 1.1.0 无 #[test]/tests 目录/[dev-dependencies]/Makefile test 目标
#    → 输出 HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests", discovered:0, ...}
```

上游无测试套件（N=0），无通过率可言；消费者验证全部通过。

## 交付物

| 文件 | 说明 |
|------|------|
| lib/lv2/bankstown.lv2/bankstown.so | LV2 插件二进制（Rust cdylib，导 lv2_descriptor） |
| lib/lv2/bankstown.lv2/bankstown.ttl | 插件元数据（12 端口） |
| lib/lv2/bankstown.lv2/manifest.ttl | LV2 bundle 清单 |

## 注意事项

- **上游测试为本地实测：上游 1.1.0 无任何测试套件，test_package 的消费者
  验证为鸿蒙特有补充（LMBS 新增用例）。** CI 侧通过 test_package 的
  HMBS_TEST_PACKAGE_RESULT / HMBS_UPSTREAM_TEST_RESULT 标记接入门禁。
- Cargo `[patch]` 与 `--locked` 冲突：本配方 build 不带 --locked。
- OHOS dlopen/加载需要 code-sign：RUSTFLAGS 在 sysroot 存在时加
  `-Wl,--code-sign`；若真机加载报签名错误，需确认工具链 code-sign 链完整。
- 若未来 rust-lv2 上游支持 OHOS（target_os=ohos 分支），可去掉 vendor patch。
