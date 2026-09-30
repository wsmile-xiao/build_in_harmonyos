# blst

## 简介

blst 是 Supranational 维护的 **BLS12-381 签名库**：用 C 实现 BLS 签名/验签、
聚合签名、hash-to-curve、pairing 与 G1/G2 群运算，关键路径由**手写汇编**加速，
被 Ethereum 生态（共识层客户端）广泛使用。

## 功能概述

- BLS12-381：G1/G2 群运算、pairing（miller loop + final exponentiation）
- 签名方案：min_pk（公钥 G1 / 签名 G2）与 min_sig（公钥 G2 / 签名 G1）
- hash-to-curve：`blst_hash_to_g1/g2`、`blst_encode_to_g1/g2`，符合 RFC 9380
- 序列化：G1/G2 点压缩与解压、scalar 大端/小端转换
- 批量操作：聚合签名、批量解压、多标量乘（Pippenger）
- 多语言绑定：Go / Rust / Python / Java / C# / node.js / Zig / Emscripten

## OHOS 适配

- 上游 `build.sh` 以 `CC/CFLAGS` 环境变量驱动，配方按 R33 从
  `tools.build:compiler_executables` 注入 clang/llvm-ar/llvm-ranlib，
  不使用 `${CC}`；R9 串行构建。
- `src/asm/*-armv8.pl` 是 **9 个 Perl 汇编生成器**。鸿蒙 PC 自带 perl 5.42.0，
  9 个生成器全部实跑通过，且产出的 `build/elf/*-armv8.S` 与仓库内已提交版本
  **字节一致**。
- `build/assembly.S` 按 `__aarch64__` + `__ELF__` 分发到 `elf/*-armv8.S`；
  编译后的 `libblst.a` 内含 **20 个 AArch64 汇编例程**（`blst_sha256_block_armv8`、
  `mul_mont_384`、`add_mod_384`、`ct_inverse_mod_384`、`sqr_mont_384` 等）。
  `test_package/ohos_abi_check.py` 对其中 5 个做断言——**纯 portable 构建会在该层失败**。
- 上游**没有 C 测试程序**（全仓无 `int main` 的 `.c` 测试）；C 库由
  `bindings/go`（28 个 Test）与 `bindings/rust`（cargo 实际枚举 **29** 个用例）
  间接测试，其 CI 矩阵含 `ubuntu-24.04-arm`。
  > Rust 用例数按 **cargo 枚举值 29** 计，而非 `grep '#[test]'` 得到的 23：
  > `lib.rs` 的 `macro_rules! sig_variant_impl` 体内含 6 个 `#[test]`，
  > 被 `pub mod min_pk` 与 `pub mod min_sig` 各展开一次（+6），加上宏外 2 个，
  > `lib.rs` 共产生 14 个；`13 + 14 + 2 = 29`。此处刻意取**更严格**的分母。
- 两套绑定测试**都在鸿蒙 PC 真机上原生跑通**：
  - Go：安装官方 `go1.23.4.linux-arm64` 并经 `binary-sign-tool -selfSign 1`
    签名后，**28/28 通过**（cgo 直接编译 AArch64 汇编）。
  - Rust：使用官方 **`aarch64-unknown-linux-ohos` host** 工具链
    （rustc/cargo 1.98.1，**不是**交叉编译搬运），
    `cargo test --lib` → **29/29 通过**；`build.rs` 经 `cc` crate 就地编译
    `src/server.c` + `build/assembly.S`。
    > 必须选 `-ohos` host：同版本的 `-musl`/`-gnu` host 在本内核上启动即
    > SIGSEGV（对照实验：设备 clang 产出的静态、static-PIE、多线程、
    > 20 MB 大二进制均正常运行，故属 host 运行时不兼容）。
- **上游合计 N = 28 (Go) + 29 (Rust) = 57**；执行 57，通过 57，失败 0；
  执行覆盖率 57/57 = 100%，已执行通过率 57/57 = 100%。
- 零补丁：所有适配点均在配方层完成，未修改上游源码，未删除或放宽任何测试。

## 交付物

| 文件 | 说明 |
|---|---|
| `lib/libblst.a` | 静态库（含 AArch64 汇编） |
| `lib/libblst.so` | 共享库 |
| `include/blst.h` | 主 API |
| `include/blst_aux.h` | 辅助 API（hash_to_curve 便捷封装等） |
| `include/blst.hpp` | C++ 封装 |
