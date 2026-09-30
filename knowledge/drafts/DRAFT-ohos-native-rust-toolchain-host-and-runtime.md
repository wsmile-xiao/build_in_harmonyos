# DRAFT: OHOS PC 上跑 Rust 工具链——host 选择与运行时四件套

## 问题场景

在 HarmonyOS PC（aarch64, musl）上跑上游 Rust 测试套件时，一路踩到六类报错。
它们的**根因不同、修法不同**，但症状都像"Rust 在鸿蒙上跑不起来"，
很容易被误判成平台不支持而放弃整套测试。

| # | 症状 | 真实根因 | 一句话修法 |
|---|---|---|---|
| 1 | `rustup-init` 签名后 `Signal 11`，无任何输出 | 用了 `-musl` host | 换 `-ohos` host |
| 2 | rustc 报 `libgcc_s.so.1` 缺失 + SIGSEGV | 同上（musl host 的 driver .so 要 GCC 版本化 `_Unwind_*`） | 换 `-ohos` host，该依赖消失 |
| 3 | `linker 'cc' not found` | 设备无 `cc` | `config.toml` 指 `linker = clang` |
| 4 | `SSL certificate ... unable to get local issuer certificate (20)` | cargo 的 OpenSSL 找不到 CA | `SSL_CERT_FILE=/etc/ssl/certs/cacert.pem` |
| 5 | `Error loading shared library libssl.so` | OHOS 只有 `libssl.so.3` | 符号链接桥接 `libssl.so -> libssl.so.3` |
| 6 | 签名后 `Permission denied` | `binary-sign-tool` 丢可执行位 | 签名后 `chmod +x` |

## 根因

### 1. 关于 host：这不是"平台不支持 Rust"

Rust 官方对 `aarch64` 发布了**三个** host tarball，版本号可以完全一样：

- `aarch64-unknown-linux-gnu`
- `aarch64-unknown-linux-musl`
- `aarch64-unknown-linux-ohos`

只有第三个的运行时能在本内核启动。前两个启动即 SIGSEGV。

**排除平台因素的对照实验**（同一台机器，用设备自带 clang 编译）：

| 试验 | 结果 |
|---|---|
| `-static` 静态二进制 | ✅ 正常 |
| `-static-pie` | ✅ 正常 |
| `pthread_create` / `pthread_join` | ✅ 正常 |
| 20 MB 附加段二进制 | ✅ 正常 |

所以不能下"OHOS 不支持静态链接 / static-PIE"的结论——**问题在 host 运行时**。

### 2. 关于 `_Unwind_*`：选对 host 后此问题不存在

`-musl` host 的 `librustc_driver-*.so` 的 `DT_NEEDED` 是
`libgcc_s.so.1` + `libc.so`，需要的符号带 GCC 版本标签：

```
_Unwind_Resume@GCC_3.0        _Unwind_RaiseException@GCC_3.0
_Unwind_Backtrace@GCC_3.3     _Unwind_GetIPInfo@GCC_4.2.0   ...
```

OHOS 的 `libc.so` 只导出 `__gnu_Unwind_Find_exidx`，`libc++_shared.so`
一个 `_Unwind_*` 都不导出——**它的 unwinder 是静态链进各二进制**的
（`libunwind.a` 在 SDK 里，但那是静态库）。

用 SDK 的 `libunwind.a` 造 `libgcc_s.so.1` shim 确实能让
`Error loading shared library` 消失，但**仍然 SIGSEGV**——因为同一个 host
不兼容问题还在。**选对 `-ohos` host 后，`librustc_driver.so` 只 `NEEDED libc.so`，
这条依赖压根不存在**。

> 教训：遇到 `_Unwind_*` 未定义，先回去检查 host 是否选错，
> 不要一头扎进造 shim。

### 3. 关于工具链以外的三件事

- **linker**：设备只有 clang/clang++，Rust 默认 linker 名是 `cc`。
- **CA**：cargo 用自己的 OpenSSL 做 HTTPS，与 curl 的 CA 探测互相独立；
  curl 能拉 crates.io 不代表 cargo 能。
- **SONAME**：`libssl.so.3` 的 SONAME 就是 `libssl.so.3`；
  cargo 的 `DT_NEEDED` 写的是 `libssl.so`。符号链接即可，不必改 SONAME。

## 解决方案

```bash
# 0. 确认 OHOS host 有官方发布（三个都要 200）
for c in rustc cargo rust-std; do
  curl -sI https://static.rust-lang.org/dist/$c-1.98.1-aarch64-unknown-linux-ohos.tar.xz | head -1
done

# 1. 装三个 -ohos 组件
PREFIX=$HOME/rust-ohos
for c in rustc cargo rust-std; do
  tar xf $c-1.98.1-aarch64-unknown-linux-ohos.tar.xz
  (cd $c-1.98.1-aarch64-unknown-linux-ohos && \
     bash ./install.sh --prefix=$PREFIX --disable-ldconfig)
done

# 2. 签名 + 补可执行位（两步都要）
for f in $(find $PREFIX -type f \( -name "*.so" -o -perm -u+x \)); do
  binary-sign-tool sign -inFile "$f" -outFile "$f.s" -selfSign 1 && chmod +x "$f.s" && mv "$f.s" "$f"
done
chmod +x $PREFIX/bin/*

# 3. 确认 host
$PREFIX/bin/rustc -vV | grep host      # → host: aarch64-unknown-linux-ohos

# 4. linker
mkdir -p $HOME/.cargo
cat > $HOME/.cargo/config.toml <<'EOF'
[target.aarch64-unknown-linux-ohos]
linker = "/data/service/hnp/bin/clang"
EOF

# 5. OpenSSL / zlib 桥接
L=$PREFIX/cargolibs && mkdir -p $L
HB=/storage/Users/currentUser/.harmonybrew/lib
ln -sf $HB/libssl.so.3    $L/libssl.so
ln -sf $HB/libcrypto.so.3 $L/libcrypto.so
ln -sf $HB/libz.so        $L/libz.so

# 6. 运行时环境
export PATH=$PREFIX/bin:$PATH
export LD_LIBRARY_PATH=$L:$PREFIX/lib
export SSL_CERT_FILE=/etc/ssl/certs/cacert.pem
export CARGO_HTTP_CAINFO=/etc/ssl/certs/cacert.pem

# 7. C/C++ 依赖（cc crate）
export CC_aarch64_unknown_linux_ohos=/data/service/hnp/bin/clang
export AR_aarch64_unknown_linux_ohos=/data/service/hnp/bin/ar

# 8. 跑单元测试（doc-test 用 --lib 规避）
cargo test --lib
```

## 已知边界

- **`rustdoc` 未随 `-ohos` host 发布**：`ls $PREFIX/../rustc-.../rustc/bin/`
  只有 `rust-gdb / rust-gdbgui / rust-lldb / rustc`，没有 `rustdoc`。
  因此 `cargo test`（不带 `--lib`）会在 doc-tests 阶段失败。
  doc-test 不计入上游用例数，用 `cargo test --lib` 即可。
- 换 Rust 版本时先重查 host 是否仍在发布列表（`-ohos` 是较新的 host，
  不要假定历史版本都有）。

## 验证

blst 0.3.17 的 Rust 绑定套件在鸿蒙 PC 上真机跑通：

```
running 29 tests
test result: ok. 29 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 9.86s
```

`build.rs` 通过 `cc` crate 在设备上直接编译 `src/server.c` +
`build/assembly.S`（AArch64 汇编），断言全过。工具链为
`rustc 1.98.1` / `cargo 1.98.1`，host `aarch64-unknown-linux-ohos`。
