# conan-verify 跳过门禁的人工补测（libgmpxx 6.3.0）

- 被测产物：`libgmpxx/6.3.0@ohpcd/stable`（干净轮 `conan create`，见 reports/conan-create.log）
- 为什么需要本文件：本包是**纯静态库**（安装树内无 `bin/` 可执行文件、无 ELF 动态产物），
  `conan-verify` 的 L2 / L4 门禁必然走「跳过」分支；官方版报告还会把 L2/L4/L5 的
  `✅ PASS` 与 `⏭️ 跳过（无 cache 路径）` 并列打印。按 `notes/device-facts.md` §二.17 的
  口径，二者并存时**以「跳过」为准**，跳过项不计 PASS，须人工补测后才可作为证据。

## 1. 产物清单核对（G4 人工复核）

命令：`conan cache path libgmpxx/6.3.0@ohpcd/stable:<package_id>` 后 `find <pkg> -type f`

实测安装树（8 个文件，与 `conanfile.py` 的 `package()` / `package_info()` 声明一致）：

```
conaninfo.txt
conanmanifest.txt
include/gmpxx.h
lib/libgmpxx.a
lib/pkgconfig/gmpxx.pc
share/info/gmp.info
share/info/gmp.info-1
share/info/gmp.info-2
```

实测文件类型（`file`）：`lib/libgmpxx.a` = `ar archive`；`include/gmpxx.h`、
`lib/pkgconfig/gmpxx.pc`、`conaninfo.txt`、`conanmanifest.txt` = ASCII text；
`share/info/*` = data。**包内无 ELF 文件。**

`package()` 裁剪结果核对（避免与 `gmp/6.3.0` 双份安装）：

| 应裁剪项 | 实测 |
|---|---|
| `lib/libgmp.a` | absent |
| `include/gmp.h` | absent |
| `lib/pkgconfig/gmp.pc` | absent |
| `*.la`（全树） | 0 个 |

## 2. L2 的替代验证（真跑消费者，非链接空转）

L2 的本意是「产物在真机上可加载/可运行」。本包无 `bin/`，替代验证 = `test_package`
消费者程序在设备上真实执行并断言计算结果：

- `reports/conan-create.log`：`RUN: ./test_gmpxx` →
  `libgmpxx test_package: all assertions passed`
- 5 项断言（`test_package/test_gmpxx.cpp`，比对真实数值而非仅链接成功）：
  mpz 大整数平方 `12345678901234567890^2`、`2^100` 十进制位数 == 31、
  `mpq 1/3 + 1/6 == 1/2`、`mpf 0.5 * 6 == 3`、`operator<<` 经 libgmpxx 非内联插入器输出 `4096`
- 同轮 W3 本地 CI 汇总：`Total: 1 / Success: 1 / Failed: 0 / Pass rate: 100.0% (1/1)`
  （`reports/w3-local-ci.log`）

## 3. L4 不适用的判据

`lib/libgmpxx.a` 是 ar 归档（无 ELF header、无动态段），包内无任何 ELF 文件（见 §1 的
`file` 实测），因此 DYN / RELRO / BIND_NOW / PIE 等 checksec 指标对本包产物不适用；
`libgmp.a` 的静态安全属性归 `gmp/6.3.0` 包，不在本包范围内。

## 4. L5 的实测结论与基线口径

- `reports/baseline.json` 在本轮落盘（2026-09-19 20:47，8 个条目），与当轮安装树逐项一致，
  例如 `lib/libgmpxx.a`（size 46468、sha256_16 `1f36e7bd6806f4ac`）、
  `include/gmpxx.h`（size 129502、sha256_16 `b287e1197a745582`）、
  `lib/pkgconfig/gmpxx.pc`（size 272、sha256_16 `529630d05ac99370`）。
- 20:57 轮（finish 内嵌验证）报告 `L5: ✅ PASS（产物与基线完全一致，8 个文件）`。
- 同轮另一次同源构建（20:58–21:07，finish 内嵌 W3）产出的 `lib/libgmpxx.a` 与基线字节级
  不同（sha256 `05e4d2f8…`、大小同为 46468 B）：同一配方/源码的两次构建**并非字节可复现**，
  差异位于 ar 归档成员头（时间戳类元数据）。更早一轮曾删除并重立基线，该轮旧基线未留副本，
  其差异成因无法用副本复核——详见 `notes.md` 的「L5 基线口径说明」。
