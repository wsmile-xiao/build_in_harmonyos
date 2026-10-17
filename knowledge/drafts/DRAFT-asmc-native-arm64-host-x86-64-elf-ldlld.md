# Draft: Native ARM64 host assembles x86/x86-64 target and links a real x86-64 executable ELF

> Status: DRAFT | Source: asmc-linux v2.39 (OpenHarmony PC), PR #6565 | 原则: 无
> 严重度: 🔴 high | 分类: toolchain/aarch64/linker/elf/x86-64/cross-target | 自动修复: ✅ batch-command

> **结构化数据**: [graph](../knowledge/graph/DRAFT-asmc-native-arm64-host-x86-64-elf-ldlld.kv) 对应 draft .kv

---

## 错误特征

```
ld: unsupported emulation 'elf_x86_64'          (GNU ld on aarch64 OHOS — only aarch64/arm emulations)
ld.lld: cannot find entry symbol main           (assembler emitted all symbols STB_LOCAL)
ld.lld: non-local symbol found at index < sh_info  (.symtab not locals-first)
```

## 根因

- 主机为 aarch64 OHOS（clang 15.0.4，GNU ld 只有 aarch64/arm 仿真），缺少 `elf_x86_64` 仿真；
- 汇编器（Asmc ARM64 原生移植）把所有符号（含 `name proc`）输出为 STB_LOCAL，且 `.symtab`
  未按 ELF 规范 LOCAL 在前/GLOBAL 在后，导致 ld.lld 无法解析入口符号。

## 首错（First Error）

首个可复现阻塞器是 aarch64 OHOS 上的 GNU ld：`ld: unsupported emulation 'elf_x86_64'`
（GNU ld 只内置 aarch64/arm 仿真，无 elf_x86_64）。随后是 ld.lld 报 `cannot find entry
symbol main`（汇编器把所有符号输出为 STB_LOCAL）与 `non-local symbol found at index < sh_info`
（.symtab 未按 LOCAL 在前/GLOBAL 在后的规范布局）。

## 诊断顺序（Diagnosis Order）

1. 在原生 ARM64 host 上 `make rebuild`——绝不使用仿真/模拟；
2. `readelf -h` / `readelf -s` 检查产物：确认是 ELF64 x86-64 REL (.o)，并核对 .symtab
   顺序与 bind 类型；
3. 若链接器为 GNU ld 且报 unsupported emulation 'elf_x86_64'，改用 `ld.lld 15.0.4`
   （`ld.lld --help` 展示 target emulations，其与主机架构无关）；
4. `ld.lld -m elf_x86_64 -static -e main` 链接；`readelf -h` 验证 E_TYPE=EXEC（x86-64）
   且 Entry 非 0；仅 REL (.o) 不算可执行产物。

## 失败替代方案（Fallback）

若 ld.lld 不可用：枚举本机全部链接器（`ld -V`、`ld.lld --help`、`clang --print-targets`），
报告最早可复现阻塞器及精确 target/emulation 支持情况；不伪造 EXEC。

## 验证边界（Validation Boundary）

- 必须 `readelf -h` 证明 E_TYPE=EXEC（x86-64）且 Entry 非 0——REL (.o) 不是可执行产物；
- 证据只能是真实 r208-r211 日志/工件：635/0 manifest、105/0 upstream tests、
  native ARM64 host 执行、ld.lld x86-64 EXEC。

## 解决方案

1. 主机/目标架构分离：host=aarch64（asmc_native 静态 ELF），target=x86/x86-64（.o ELF64 x86-64 REL 与原始 .bin）。
2. 修复汇编器 ELF 写出：
   - `name proc` 符号输出 STB_GLOBAL；
   - `.symtab` 先写 LOCAL 再写 GLOBAL，`sh_info = 1 + nloc`；
   - 重定位符号索引按重排后的表映射。
3. 链接：使用已存在的 `ld.lld 15.0.4`（`-m elf_x86_64 -static -e main`），生成真实 x86-64
   EXEC ELF（Entry 0x201167，两个 LOAD 段）。
4. 禁用项：QEMU/Wine/仿真器/固定 ELF 字节/stub 可执行文件。

## 验证证据（r208–r211）

- 635-source manifest：`aarch64_port/r210_evidence/t4_manifest_635.txt` → PASS=635 FAIL=0
- 105 upstream tests：`aarch64_port/r210_evidence/t4_105_results.txt` → PASS=105 FAIL=0
- conan create + smoke：`aarch64_port/r210_evidence/t4_conan_create.log` → smoke test OK（原生运行 + x86-64 目标 + ld.lld 链接）
- x86-64 EXEC ELF：`aarch64_port/r209_evidence/e2d_x64_exec.elf`（ELF64 EXEC X86-64 Entry 0x201167）
  / `aarch64_port/r210_evidence/ohos_smoke/smoke.elf`
- 符号表修复：asmc_asm.c（proc→GLOBAL）、asmc_elf.c（locals-first/sh_info/reloc 映射）

## 适用边界

- 适用于任何在 aarch64 OHOS 上需要生成 x86/x86-64 目标（对象/程序）的工具链型程序。
- 不适用于需要 QEMU/Wine/固定字节/stub 的场景（禁止）。

## 禁止

- QEMU/Wine/仿真器、固定 ELF 字节、stub 可执行、伪造"已运行/已合入"；
- 把 x86/x86-64 REL 对象 (.o) 当作 executable ELF 汇报，或在无 `readelf -h` E_TYPE 证明下
  声称已生成可执行产物（REL 是可重定位对象，不是可运行程序）。

## Provenance

- source_event: archives/a/asmc-linux/v2.39/manifest.yaml
- source_pr: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/6565
- source_commit: 1a67d96bd004938572e8de9fdfcb0c0abd22e305