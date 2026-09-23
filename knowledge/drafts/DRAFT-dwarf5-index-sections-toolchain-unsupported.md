# DRAFT-dwarf5-index-sections-toolchain-unsupported — DWARF5 索引节 vs 只认 DWARF4 的老工具：编译包装降级 + 剥离 crt 调试信息

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-11
> **Severity**: 🟡 medium | **Category**: dwarf / toolchain / testing / debug-info

## 相关既有条目（同族差异化定位）

| 既有条目 | 同族点 | 本 skill 的增量（差异化） |
|---------|--------|--------------------------|
| **E173**（Perl XS：crti.o/crtbeginS.o 缺失）| 同属"OAOHOS 工具链 crt 文件问题" | E173 是 crt **缺失**导致链接失败、改用 `-nostartfiles` 绕过；本条目是 crt **存在但带 DWARF5**、仍必须链接它（否则 printf 等符号缺失），只是需要 `objcopy --strip-debug` 预处理其调试节 |
| **E007**（config.guess 无 HarmonyOS 分支）| 同属"工具链默认假设与 OHOS 不符" | E007 解决交叉编译三元组识别；本条目解决**调试信息版本**能力错配，二者独立可叠加 |
| **DRAFT-ohos-otmpfile-tmpdir-shim** | 同为"运行/构建环境适配 shim" | 无重叠——该条目处理临时文件目录，本条目处理 DWARF 调试节 |

> 查证（2026-09-11）：`gdwarf`、`debug_str_offsets`、`DW_FORM_strx`、`DWARF 5` 在
> knowledge/doc 与 knowledge/drafts 下命中 **0 条**——本条目为空白领域。

## Scope（何时用）

在 HarmonyOS PC 上执行"上游测试需要编译带调试信息的 ELF 作输入，而被测工具只支持
DWARF4 及以下"的测试套件时，若出现：

- 被测工具报 `Unknown debugging section .debug_str_offsets`（或 `.debug_addr` /
  `.debug_rnglists` / `.debug_line_str`）后中止；
- 已尝试给用户代码加 `-gdwarf-4` 但**无效**（关键：链接进来的 crt 目标本身是 DWARF5）；
- `readelf --debug-dump=info <bin> | grep Version:` 显示**多个 CU**且版本混杂
  （用户代码 4、crt 5）。

典型实例：dwz 0.16 的 DejaGNU testsuite（`dwz <bin>` 直接报错）。同类工具：老版本
elfutils、binutils < 2.30、gdb < 8、任何只解析已知调试节表的工具。

## 症状

```
$ dwz hello -o hello.dwz
dwz: hello: Unknown debugging section .debug_str_offsets
```

```
$ readelf --debug-dump=info hello | grep Version: | sort | uniq -c
      1    Version:       4     # 用户代码（已加 -gdwarf-4）
      6    Version:       5     # ← Scrt1.o/crti.o/clang_rt.crtbegin.o/crtend.o
```

## 根因

1. **工具侧**：老工具的调试节表是枚举式的（dwz 的 `debug_sections[]`），DWARF5 新增
   节不在表内 → 报 Unknown 并 `return 1`。
2. **工具链侧**：OHOS SDK 的 clang 15 默认 DWARF5；且 **crt 目标文件本身以 DWARF5
   编译**。因此「用户代码降级」不够——链接后 6 个 DWARF5 CU 仍在。

## 方案（推荐）

**编译包装 + 剥离 crt 调试信息**（`rec_approach: compiler-wrapper-downgrade-plus-crt-strip`）

1. 预处理 crt：把 `Scrt1.o/crt1.o/crti.o/crtn.o`（sysroot）与
   `clang_rt.crtbegin.o/clang_rt.crtend.o`（clang 资源目录）复制到独立目录，
   逐个 `objcopy --strip-debug`。
2. 包装脚本供 `make CC=<wrapper> CXX=<wrapper2>` 使用：
   - 剔除所有 `-g*`，在**参数末尾**追加 `-g -gdwarf-4`。
     ⚠️ **顺序关键**：`-gdwarf-4 -g` 会被 `-g` 重置回默认 DWARF5。
   - 链接阶段（无 `-c/-E/-S`）加 `-nostartfiles` + 显式传入第 1 步的 crt。
   - 目标自带 `-nostdlib/-nostartfiles` 时（如 `start.o`）**不注入**，否则 `_start`
     重复定义。
   - 被测工具自身（如 `dwz-for-test`）也要用同一包装编译——它处理自己时同样报错。
3. 注意 `make` 的 staleness 判断：改了 CC 未必触发重建，必须先 `rm -f` 目标，
   再核对时间戳与 `readelf` 版本确认**真的重建了**。

## 验证

```sh
# 1) 二进制的 DWARF 版本应只有 4
readelf --debug-dump=info hello | grep Version: | sort | uniq -c
# 期望：仅 "1  Version: 4" 一行

# 2) DWARF5 索引节应消失
readelf -S hello | grep -cE 'debug_str_offsets|debug_addr'
# 期望：0

# 3) 被测工具应能处理
dwz hello -o hello.dwz && echo OK
```

## 备选（fallback）

`per-section-objcopy-removal`：若输入是预编译产物、无法改编译命令，可
`objcopy --remove-section=.debug_str_offsets --remove-section=.debug_addr
--remove-section=.debug_rnglists <bin>`。注意会**连锁暴露下一个节名**（删完
str_offsets 报 addr，再报 rnglists），需循环至工具接受——仅适合少量固定产物。

## 禁止

- ❌ **给老工具补 DWARF5 解析**（`patch dwz.c` 加索引节支持）：属上游功能开发，
  远超适配边界，且每次上游升级补丁失效。
- ❌ **跳过涉及调试信息的用例**（填 N/A 或 excluded）：降级编译即可真实执行，
  跳过属「有可运行子集未尝试」（rule 4）。

## 实证

- **dwz/0.16（PR #9459）**：上游 DejaGNU testsuite 通过率 **0/62 → 48/62**，其中
  **24+ 个用例**由本方案解锁（`objcopy-strip-debug`、`multifile*`、
  `odr-*`、`low-mem-die-limit*` 等）。
- 同套件另需的配套修复（见 DRAFT-dejagnu-toolchain-assembly-ohos）：config.guess
  OHOS 识别（E007）、DejaGNU spawn `-nottyinit`（E272）、GNU readelf 替代
  eu-readelf、被测工具硬编码 `/tmp` 改为读 `TMPDIR`。
