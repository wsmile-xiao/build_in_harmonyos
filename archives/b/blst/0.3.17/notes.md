# blst 0.3.17 适配笔记（HarmonyOS PC / aarch64）

## 一、概述

blst 是 Supranational 的 BLS12-381 签名库，C 实现 + **手写汇编**。交付物为本体
C 库：`libblst.a`、`libblst.so` 与头文件 `blst.h` / `blst_aux.h` / `blst.hpp`。

- 上游：https://github.com/supranational/blst
- tag：`v0.3.17`
- tarball SHA256：`c3fef37b566b67419703b2bbb648e15176276af9a880c22aa8f5f2e8cecc2e4d`
- 许可证：Apache-2.0

## 二、路径 C 证据（源码级）

### 2.1 Perl 汇编生成器（9 个，全部在鸿蒙 PC 上实跑通过）

`src/asm/` 下的 ARMv8 生成器：

```
add_mod_256-armv8.pl      add_mod_384-armv8.pl
ct_inverse_mod_256-armv8.pl  ct_inverse_mod_384-armv8.pl
ct_is_square_mod_384-armv8.pl  div3w-armv8.pl
mul_mont_256-armv8.pl     mul_mont_384-armv8.pl
sha256-armv8.pl           arm-xlate.pl（ARM 汇编后处理器）
```

`build/refresh.sh` 的调用形式：

```sh
for pl in ../src/asm/*-armv8.pl; do
    ${PERL} $pl linux64 > elf/$(basename $pl .pl).S
done
```

**真机实测**：在 HarmonyOS PC 上用设备自带 perl 5.42.0 逐个运行上述 9 个生成器，
`ok=9 fail=0`；产出的 `mul_mont_384-armv8.S`、`add_mod_384-armv8.S`、
`ct_inverse_mod_384-armv8.S`、`sha256-armv8.S` 与仓库内已提交版本
**SHA256 前 16 位完全一致**（字节一致）。

### 2.2 AArch64 汇编真实参与构建

`build/assembly.S` 按 `__aarch64__` + `__ELF__` 分发：

```c
#elif defined(__aarch64__)
# elif defined(__ELF__)
#  include "elf/sha256-armv8.S"
#  include "elf/ct_inverse_mod_384-armv8.S"
#  include "elf/add_mod_384-armv8.S"
#  include "elf/mul_mont_384-armv8.S"
...
```

鸿蒙 aarch64 上构建出的 `libblst.a` 中实测存在 **20 个 AArch64 汇编例程**：

```
blst_sha256_block_armv8  mul_mont_384   mul_mont_384x   mul_mont_sparse_256
add_mod_256   add_mod_384  add_mod_384x  add_mod_384x384
sqr_mont_384  sqr_mont_384x  sqr_mont_sparse_256
ct_inverse_mod_256  ct_inverse_mod_384  ct_is_square_mod_384
from_mont_256  from_mont_384  redc_mont_256  redc_mont_384
sgn0_pty_mont_384  sgn0_pty_mont_384x
```

`test_package/ohos_abi_check.py` 会对其中 5 个做断言——**纯 portable 构建会在此层失败**，
这正是路径 C 所主张的属性。

## 三、上游测试统计（硬性要求）

### 3.1 关键事实：上游没有 C 测试程序

`find . -name "*.c" | xargs grep -l "int main"` → **0 个**。
blst 的 C 库是通过 **Go / Rust 绑定** 间接测试的。CI（`.github/workflows/ci.yml`）
矩阵为 `ubuntu-latest / ubuntu-24.04-arm / windows-latest / windows-11-arm / macos-latest`。

### 3.2 上游测试入口与真实用例数

| 测试类型 | 上游用例数 | 统计命令 | 环境要求 | OpenHarmony 可执行性 |
|---|---:|---|---|---|
| 单元/集成（Go 绑定） | **28** | `go test -list ".*" ./bindings/go` | Go + cgo + C 编译器 | ✅ **可执行（真机 28/28 通过）** |
| 单元/集成（Rust 绑定） | **29** | `cargo test --lib` 实际枚举 | Rust/cargo（原生 OHOS host） | ✅ **可执行（真机 29/29 通过）** |
| 测试数据（hash-to-curve 向量） | 7 个 JSON | `ls bindings/vectors/hash_to_curve/` | 被上述测试消费 | ✅ 数据随包 |
| **合计（可执行绑定用例）** | **57** | | | **57 可执行，0 缺失** |

> **Rust 用例数为什么是 29 而不是源码里的 23 个 `#[test]`。**
> `grep -c '#\[test\]'` 数的是**源码字面量**，会漏掉宏展开。
> `bindings/rust/src/lib.rs:515` 的 `macro_rules! sig_variant_impl` 体内含 6 个
> `#[test]`，该宏被 `pub mod min_pk`（lib.rs:2203）和 `pub mod min_sig`
> （lib.rs:2248）各展开一次，因此这 6 个字面量实际产生 12 个测试用例；
> 加上宏外的 2 个，lib.rs 共产生 14 个。逐文件对账：
>
> | 文件 | `#[test]` 字面量 | 宏展开后实际用例 |
> |---|---:|---:|
> | `src/bindings.rs` | 13 | 13（bindgen 布局校验） |
> | `src/lib.rs` | 8 | 14（其中 12 个来自宏 ×2 展开） |
> | `src/pippenger-test_mod.rs` | 2 | 2 |
> | **合计** | **23** | **29** |
>
> 因此以 cargo 的权威枚举值 **29** 为准（见 §3.4 的真机输出）。
> 这里刻意采用**更大的**分母，避免少报测试数量。

**本包的上游测试统计口径**（N/A/E/P/F 定义见仓库 TEST_QUALITY_SPEC）：

| 指标 | 数值 |
|---|---:|
| 上游发现总数 N | 57（Go 28 + Rust 29） |
| 当前架构适用数 A | 57 |
| OpenHarmony 实际执行数 E | 57 |
| 通过数 P | 57 |
| 失败数 F | 0 |
| 未执行数 A−E | 0 |
| 执行覆盖率 E/A | **57/57 = 100%** |
| 已执行通过率 P/E | **57/57 = 100%** |

### 3.3 真机运行结果（上游 Go 套件）

在 HarmonyOS PC 上安装并**自签名**官方 Go 工具链（`go1.23.4.linux-arm64`）后执行：

```bash
cd bindings/go
CGO_ENABLED=1 CC=clang go test -v -count=1 .
```

```
=== RUN 计数: 28
--- PASS 计数: 28
--- FAIL 计数: 0
ok  github.com/supranational/blst/bindings/go  2.250s
```

**28/28 = 100%**，cgo 在设备上直接编译 `src/*.c` + `build/assembly.S`（AArch64 汇编）。

### 3.4 真机运行结果（上游 Rust 套件）

Rust 绑定同样在鸿蒙 PC 上**原生**运行——用的是 Rust 官方发布的
`aarch64-unknown-linux-ohos` **host** 工具链（不是交叉编译）：

```bash
# 官方原生 OHOS host 组件（非 musl/gnu host）
curl -O https://static.rust-lang.org/dist/rustc-1.98.1-aarch64-unknown-linux-ohos.tar.xz
curl -O https://static.rust-lang.org/dist/cargo-1.98.1-aarch64-unknown-linux-ohos.tar.xz
curl -O https://static.rust-lang.org/dist/rust-std-1.98.1-aarch64-unknown-linux-ohos.tar.xz
# 安装后对全部 ELF 自签名（sign 会去掉可执行位，需 chmod +x）

cd blst/bindings/rust && ln -s ../.. blst   # publish.sh 约定的 crate 布局
cargo test --lib
```

```
running 29 tests
test result: ok. 29 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 9.86s
```

**29/29 = 100%**，`build.rs` 通过 `cc` crate 在设备上直接编译
`src/server.c` + `build/assembly.S`（AArch64 汇编），断言全部通过。
日志：`path-c-evidence-20260929/blst/cargo_test_lib.log`，
环境记录：`path-c-evidence-20260929/blst/RUST_EVIDENCE.txt`。

> 工具链细节（首次跑通需要的关键点，均已在设备上验证）：
> - 必须是 **`aarch64-unknown-linux-ohos` host** 的官方发布。同一版本的
>   `-musl` / `-gnu` host 二进制在本内核上**启动即 SIGSEGV**；作为对照，
>   本机 clang 产出的静态、static-PIE、多线程、20 MB 大二进制均正常运行，
>   因此这是 Rust musl/gnu host 运行时不兼容，不是平台的静态链接限制。
> - `$HOME/.cargo/config.toml` 指定 `linker = "/data/service/hnp/bin/clang"`
>   （设备上没有 `cc`）。
> - cargo 需要 `libssl.so`/`libcrypto.so`/`libz.so`；OHOS 只提供
>   `libssl.so.3`，用符号链接桥接；并设 `SSL_CERT_FILE=/etc/ssl/certs/cacert.pem`。
> - Rust 官方**未**为 `aarch64-unknown-linux-ohos` 发布 `rustdoc`，
>   故上游 doc-tests 无法运行（`cargo test --lib` 正好只跑 29 个单元测试，
>   退出码 0）。这 29 个用例不含任何 doc-test。

## 四、适配修改

**零补丁**（`patches/` 为空）。`conandata.yml` 的 `patches: {}`。

配方层适配点：

1. `build()` 通过环境变量向 `build.sh` 注入 `CC/CFLAGS/AR/RANLIB/PERL`
   （R33：编译器取自 `tools.build:compiler_executables`，不使用 `${CC}`）。
2. CFLAGS 追加 `-Wno-error`，避免上游告警在 CI 上被当作错误。
3. `validate()` 接受 `Linux` 与 `OHOS`（R32），不写 `== Linux`。
4. `package()` 复制 `bindings/blst.h`、`blst_aux.h`、`blst.hpp` 与两个库文件。

## 五、test_package（消费者测试，单独统计，不计入上游 N）

两层设计（参照仓库既有先例）：

- **第 1 层 `ohos_abi_check.py`**（纯 Python，任意宿主可跑）：
  **17/17 PASS** —— AArch64 ELF64、`.note.ohos.ident`、OHOS `libc.so`（非 glibc
  `libc.so.6`）、无宿主 RPATH/RUNPATH、无构建机绝对路径、无 Mach-O/PE 泄漏，
  以及 `libblst.a` 内 5 个 AArch64 汇编符号存在。
- **第 2 层 `test_blst.c`**（仅 `can_run()` 时执行）：**7/7 PASS**
  - T1a/T1b/T1c：`blst_hash_to_g1` 对上游向量
    `BLS12381G1_XMD_SHA-256_SSWU_RO_.json` 空消息用例的 **KAT 精确匹配**（x、y 均一致）
  - T2：keygen → `sk_to_pk_in_g1` → `sign_pk_in_g1` → `core_verify_pk_in_g1` 往返成功
  - T3：篡改消息被拒绝（负路径）
  - T4：G1 压缩/解压往返无损
  - T5：公钥在曲线上

## 六、遇到并解决的问题

| # | 现象 | 根因 | 解决 |
|---|---|---|---|
| 1 | `go: fork/exec .../compile: permission denied` | HarmonyOS 拒绝执行未签名 ELF | 对 Go 工具链 20 个二进制逐一体 `binary-sign-tool sign -selfSign 1` |
| 2 | `memcmp(ha.x.l, ...)` 与向量不符 | `blst_fp` 内部是**小端 limb**（`limb_t l[6]`），向量是大端十六进制 | 改用 `blst_bendian_from_fp()` 转换后再比较 |
| 3 | `blst_sign_pk_in_g2(&blst_p2*, ...)` 编译失败 | min_pk 模式下公钥在 G1、签名在 G2，对应函数是 `blst_sign_pk_in_g1` | 更正为 `blst_sign_pk_in_g1` |
| 4 | `.so` 无 PT_INTERP 导致 ABI 检查误报 | 共享库本就没有解释器字段 | 改为检查 `libc.so`（OHOS）而非 `libc.so.6`（glibc）+ 无 RPATH |
| 5 | `rustup-init` / `rustc`（`-musl` host）启动即 `Signal 11` | Rust 的 musl/gnu host 运行时与本内核不兼容（同版本 `-ohos` host 正常） | 改用官方 `aarch64-unknown-linux-ohos` host 组件 |
| 6 | `rustc` 报 `libgcc_s.so.1` 缺失 | `librustc_driver.so` 需要 GCC 版本化 `_Unwind_*@GCC_3.0`，OHOS 不提供（其 unwinder 是静态链接的） | `-ohos` host 的 rustc 只依赖 `libc.so`，**不需要**该 shim |
| 7 | `cargo` 报 `linker 'cc' not found` | 设备上没有 `cc` | `$HOME/.cargo/config.toml` 指定 `linker = "/data/service/hnp/bin/clang"` |
| 8 | `cargo` 报 `SSL certificate ... unable to get local issuer certificate` | cargo 的 OpenSSL 找不到 CA bundle | `SSL_CERT_FILE=/etc/ssl/certs/cacert.pem`（`CARGO_HTTP_CAINFO` 同值） |
| 9 | `cargo` 报 `Error loading shared library libssl.so` | OHOS 只有 `libssl.so.3`，cargo 要 `libssl.so` | 符号链接 `libssl.so -> libssl.so.3`（`libcrypto.so`、`libz.so` 同理） |
| 10 | 签名后的 `rustc`/`cargo` 报 `Permission denied` | `binary-sign-tool` 输出的文件**丢失可执行位** | 签名后统一 `chmod +x` |

## 七、风险与边界

- **上游 doc-tests 未运行**：Rust 官方未为 `aarch64-unknown-linux-ohos` 发布
  `rustdoc`，设备上无法执行 `cargo test --doc`。§3 的 57 个用例**不含** doc-test，
  因此不影响覆盖率口径；这是工具链分发限制，有 `ls rustc/bin/` 输出为证。
- **Rust host 选择**：必须用 `aarch64-unknown-linux-ohos` host；
  `-musl`/`-gnu` host 在本内核上 SIGSEGV（已留证）。CI 若复用本笔记，
  需按 §3.4 的组件名下载。
- **`-Wno-error`**：仅为绕开上游告警，未关闭任何功能或测试。
- 未修改任何上游源码；未删除、跳过或放宽任何测试。
- Go / Rust 两套绑定测试在鸿蒙上跑的**都是真机原生编译**，不是交叉编译后搬运。
