# DRAFT-rutabaga-0.1.80-rust-ohos-rlib-adaptation：纯 Rust rlib 库在 OHOS 上的构建/链接/签名组合适配

> Status: DRAFT（knowledge/drafts/，未提升为正式 E 条目）
> Source: rutabaga 0.1.80（crates.io `rutabaga_gfx`）HarmonyOS PC 适配，2026-10-01
> Related: `DRAFT-below-ohos-unsigned-rust-toolchain`（同族前作；本条为四项增量）、E105/E154、E318、E509

## 背景

`rutabaga 0.1.80`（crates.io crate 名 `rutabaga_gfx`）是纯 Rust 的 GPU/显示半虚拟化库，
产物是 Rust 静态库 `librutabaga_gfx.rlib`（无 C API、无二进制、`autotests=false`）。
在 HarmonyOS PC（aarch64，rustc/cargo 1.97.1，目标 `aarch64-unknown-linux-ohos`）上以
conan + `tool_requires("rust-toolchain/1.97.1")` 构建时，按暴露顺序踩到五个正交问题。

同族前作 `DRAFT-below-ohos-unsigned-rust-toolchain` 已覆盖「预编译工具链 **bin** 与
`librustc_driver` 的 exec/dlopen 签名 + cargo 运行库/CA」。本条只记录它未覆盖的增量。

## 现象（错误面，按暴露顺序）

| # | 原始错误 | 实际含义 |
|---|---|---|
| 1 | `Error loading shared library libssl.so` / `Permission denied (os error 13)` | 未签名 ELF 被 OHOS loader 拒绝（不是"文件不存在/权限位"） |
| 2 | `SSL_get0_group_name: symbol not found` | cargo 1.97 需要 OpenSSL ≥ 3.5（`OPENSSL_3.2.0` 版本符号） |
| 3 | `E0463 can't find crate for 'std'`（`the aarch64-unknown-linux-ohos target may not be installed`） | `lib/rustlib` 是**符号链接**，rustc 不解析 |
| 4 | `could not exec the linker … Permission denied` / `ld.lld: error: cannot open Scrt1.o` + `unable to find library -lc` | SDK `clang` 是 `/bin/sh` 包装脚本：exec 被拒；或包装脚本 `readlink/dirname` 失败导致 sysroot 推导错误 |
| 5 | `Text file busy (os error 26)`（偶发） | HMDFS 上新写入的 build script 立即被 exec |

## 诊断

1. **签名**：OHOS loader 拒绝未签名 ELF。需要 `binary-sign-tool -selfSign 1` 的对象：
   `cargo`/`rustc`（exec），`librustc_driver-*.so`（dlopen），以及 cargo 运行期
   `libssl.so`/`libcrypto.so`（dlopen）。
2. **OpenSSL 版本门**：设备镜像自带 `libssl.so.3` 无 `SSL_get0_group_name`
   （用 `llvm-readelf --dyn-symbols` 可确认）；Harmonybrew `openssl@3-3.6.4` bottle 提供
   带 `OPENSSL_3.2.0` 版本符号的实现。`libz` 建议用平台 `/system/lib64/platformsdk`
   （旧配方引用的 `zlib-ng-compat-2.3.3_1` bottle 已 404）。
3. **rustlib 必须实体化**：`cp -a <pkg>/lib/rustlib <build>/rust-toolchain/lib/rustlib`
   （`copytree(symlinks=False)`）。符号链接时 `rustc --print sysroot` 正常但 std 找不到。
4. **linker 必须是 ELF**：SDK 目录里 `clang` 与 `aarch64-unknown-linux-ohos-clang` 都是
   `/bin/sh` 脚本，只有 `clang-15` 是可执行 ELF。配方须显式注入
   `-C link-arg=--target=aarch64-linux-ohos`、`-C link-arg=--sysroot=<sdk>/native/sysroot`、
   `-C link-arg=-D__MUSL__`。注意 conan profile 的
   `tools.build:compiler_executables={"c": "/data/service/hnp/bin/clang"}` 正指向包装脚本，
   配方里的 `_ohos_clang()` 必须**先**按 SDK 布局 glob `clang-15`，profile conf 仅用于定位目录。
5. **ETXTBSY 重试**：cargo 调用（fetch/build/test）在日志出现 `Text file busy`/`os error 26`
   时重试至 3 次即可稳定通过。

## 推荐方案（已验证）

```python
# 1) 自建签名工具链
shutil.copytree(src/"lib"/"rustlib", lib_dst/"rustlib", symlinks=False)   # 实体复制
for name in ("cargo", "rustc"): copy + binary-sign-tool -selfSign 1
for so in *.so: copy + sign
# 2) 运行期库
openssl@3-3.6.4 bottle(.so → 签名) + platform /system/lib64/platformsdk (libz)
LD_LIBRARY_PATH = [toolchain/lib, openssl3/lib, /system/lib64/platformsdk, /system/lib64]
# 3) cargo config.toml
[target.aarch64-unknown-linux-ohos]
linker = "<sdk>/native/llvm/bin/clang-15"
rustflags = ["-C","link-arg=--target=aarch64-linux-ohos",
             "-C","link-arg=--sysroot=<sdk>/native/sysroot",
             "-C","link-arg=-D__MUSL__"]
# 4) /tmp 只读 → TMPDIR/TMP/TEMP 重定向到 build folder 内可写目录
```

## 禁止策略

- ❌ 把 SDK 的 `clang` / `aarch64-unknown-linux-ohos-clang` 包装脚本当作 rustc linker。
- ❌ 把 `lib/rustlib` 以符号链接形式落到 build folder。

## 验证（真机实测）

```
$ cargo build --release --target aarch64-unknown-linux-ohos     # Finished release profile, 40.94s
$ cargo test  --release --lib --target aarch64-unknown-linux-ohos
test result: ok. 8 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out
# conan create / conan-verify(G1-G4) / W3 本地 CI 模拟 全部 EXIT=0
```

## 附：CI 侧环境注意（与库本身无关）

设备 `/tmp` 只读，而 OHOS 版 zsh 5.9 的 here-document 临时文件**不读 `TMPDIR`**
（固定 `/tmp`），导致 `ci/conan/build_and_test.sh` 中 L0i/L0m 等含 here-doc 的检查直接失败；
导出 `TMPPREFIX=<可写目录>/zsh` 后通过（W3 通过的前提）。
