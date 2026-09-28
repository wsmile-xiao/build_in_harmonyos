# intermodal 0.1.16 — 测试报告（OHOS PC aarch64）

- 测试日期：2026-09-23
- 测试平台：HarmonyOS PC 真机（aarch64，os=OHOS os.version=6.0）
- 构建 profile：ci/conan/profiles/ohos-aarch64（clang 15 / libc++ / cppstd=17 / Release）
- 测试来源：`reports/w3-local-ci.log` 的 `L*_RESULT=` 行、`reports/conan-create.log`
  的 cargo test 输出与 test_package 输出

## 1. W3 本地 CI 模拟（reports/w3-local-ci.log）

```
G0_RESULT=pass
KC_RESULT=pass
JC_RESULT=pass
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=pass: imdl --version OK
L4_RESULT=pass: patches clean
L5_RESULT=pass: bin/ has content
Build Summary: Total 1 / Success 1 / Pass rate 100.0%
```

破坏性负测试（R34）：`[sabotage] bin/ moved away` → `[ok] L1e: Negative test
confirmed — test genuinely depends on intermodal`（test_package 真实依赖产物，
非空壳）。

conan-verify（reports/conan-verify-report.md）：G1 ✅ / G2 ✅（conan create 成功）/
G3 ✅（纯可执行包，无系统同名库冲突）/ L2/L4/L5 ✅。

## 2. 上游测试（build() 内实跑，HarmonyOS PC 真机）

命令：`cargo test --release --target aarch64-unknown-linux-ohos -p imdl --lib
--bins --no-fail-fast`（见 reports/conan-create.log）

静态统计：src/ 下 52 个 `#[cfg(test)]` 模块、285 个 `#[test]` 函数
（`grep -rc '#\[test\]' src/`）。实际执行：`--lib` 目标 282 个可执行用例
（284 宏中 2 个 `#[ignored]`）+ `--bins`（main.rs 单元测试）0 个。

```
test result: FAILED. 280 passed; 2 failed; 2 ignored; 0 measured; 0 filtered out
```

**通过率：280/282 = 99.3%**（计入 ignored 为 280/284）

失败用例逐项技术原因（R51 申报）：

| 用例 | 失败原因 |
|------|---------|
| subcommand::torrent::create::tests::follow_symlinks | 测试经 `std::os::unix::fs::symlink` 在临时目录创建符号链接；本平台 HMDFS uid 映射卷**不支持创建 symlink**（os.symlink 直接 EPERM，见 notes.md 坑 #1）→ 环境限制，非被测逻辑缺陷 |
| subcommand::torrent::create::tests::symlink_root | 同上（symlink 根目录场景） |

doctest 排除说明：doctest 由 `rustdoc` 执行，rust-toolchain/1.97.1 dist 包的
rustdoc 未携带 OHOS code signature，execve 报 EACCES（errno 13）；README/doc
示例不属于单元测试契约，故测试命令限定 `--lib --bins`。

## 3. test_package 消费者测试（15/15 通过）

test_package/test_imdl.py，运行于 conan test（env=conanrun）：

```
== 鸿蒙特有测试 / HarmonyOS-specific assertions ==
[ok] B4: imdl is a non-empty regular executable file
[ok] B1: ELF machine is AArch64 (EM_AARCH64=183): e_machine=183
[ok] B2: PT_INTERP is the OHOS musl loader: interp=/lib/ld-musl-aarch64.so.1
[ok] B3: OHOS code signature present (unsigned ELF cannot execve)
== 消费者冒烟测试 ==
[ok] A1: `imdl --help` exits 0
[ok] A2: `--help` output mentions torrent subcommand
[ok] A3: `imdl --version` exits 0 and reports 0.1.16
== 功能测试 ==
[ok] F1: `imdl torrent create` exits 0（含 --announce）
[ok] F2: .torrent file created and non-empty（166 bytes）
[ok] F3: .torrent is a bencode dictionary (d...e)
[ok] F4: .torrent contains announce and info keys
[ok] F5: .torrent info dict carries the payload file name
[ok] F6: `imdl torrent show` exits 0 and shows the name
[ok] F7: `imdl torrent verify` exits 0 (re-hash OK)
[ok] F8: `imdl torrent link` prints magnet with 40-hex infohash
SUMMARY: executed=15 passed=15 failed=0 (harmonyos_specific=4)
```

## 4. verify-build（打包前门禁）

```
G1 二进制完整性 ✅ / G2 功能可用性 ✅(⚠️1) / G3 可移植性 ✅ / G4 档案完整性 ✅(⚠️1)
质量报告: PASS → .verify-passed
```

## 5. 汇总

| 层 | 数量 | 结果 |
|----|------|------|
| 上游 cargo 单元测试 | 282 执行（284 宏） | 280 通过 / 2 symlink 环境限制失败（99.3%） |
| test_package 消费者断言 | 15（含鸿蒙特有 4） | 15/15 |
| W3 本地 CI | L0/L1/L2/L4/L5 + G0/KC/JC | 全 pass |
| 破坏性负测试（R34） | 1 | 通过（测试真实依赖产物） |
