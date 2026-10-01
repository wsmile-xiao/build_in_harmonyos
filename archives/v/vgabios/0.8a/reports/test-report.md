# 测试报告 — vgabios 0.8a（LGPL'd VGABIOS）

> **项目**: vgabios（Bochs / QEMU / plex86 的 LGPL 显卡固件；8086 实模式 Option ROM）
> **测试日期**: 2026-09-30
> **测试环境**: HarmonyOS PC（`uname -s` = HarmonyOS，HongMeng Kernel 1.12.0，aarch64）
> **测试类型**: 上游测试入口核验（§一）+ 消费者侧功能测试 test_package（§二）
> **上游测试统计与 test_package 统计分开申报**（test_package 不计入上游测试）

---

## 一、上游测试清点与执行（R51 三步法）

### 1.1 清点（真实命令 + 原始输出）

| 检查项 | 命令 | 结果 | 退出码 |
|--------|------|------|:------:|
| 测试目标 | `grep -nE '^(check\|test\|tests)\s*:' Makefile` | **无输出** | 1 |
| 全部目标 | `grep -nE '^(all\|bios\|cirrus-bios\|banshee-bios\|clean\|dist-clean\|release)\s*:' Makefile` | 仅构建/清理/发布目标 | 0 |
| 测试目录 | `ls -1 tests/` | `testbios.c`、`lfbprof/` | 0 |
| ctest / meson / pytest | 全树检索 | 无 | — |
| 上游样例数据 | 全树检索 | 无 | — |
| README 声明 | `sed -n '/^Testing/,/^Copyright/p' README` | 指向 `testvga.c`（**0.8a 归档中不存在该文件**） | 0 |

原始输出留档：`reports/upstream-check.log`

### 1.2 实际执行

**上游不存在自动化测试入口**：顶层 Makefile 无 `check`/`test` 目标，
`make check` 与 `make test` 均无对应规则（命令均以
`make: *** No rule to make target 'check'. Stop.` 语义失败，见上游命令核验）。

`tests/` 下两个样例程序逐一实测：

| 样例 | 上游要求的工具链 | 实测命令 | 原始输出 | 退出码 |
|------|------------------|----------|----------|:------:|
| `tests/testbios.c` | Turbo C 2.0（DOS，`<dos.h>`/`<conio.h>`/`intr()`/`REGPACK`） | `bcc -S tests/testbios.c -o /dev/null` | `tests/testbios.c:10: error: Cannot open include file`（`#include <dos.h>`） | 1 |
| `tests/lfbprof/lfbprof.c` | Watcom C++ 10.0a + DOS4GW（`wcl386 -zq -s -d2 lfbprof.c`） | 需 `wcl386`（OHOS/本机均无该商业编译器） | 见 `tests/lfbprof/Makefile` | — |

### 1.3 上游测试统计（机器可读）

| 指标 | 数值 |
|------|:----:|
| 上游测试命令 | **无**（Makefile 无 `check`/`test`/`ctest` 目标） |
| 用例总数 | **0** |
| 通过 | 0 |
| 失败 | 0 |
| 跳过 | **0**（不适用：无测试可跑） |
| 未运行原因 | 上游 0.8a 不含任何自动化测试基础设施；`tests/` 内仅 Turbo C 2.0 / Watcom C++ 的 DOS 交互式程序，依赖上游未提供的商业编译器头文件与 DOS 运行期，**在 OHOS 上既不能编译也不能运行**（已实测取证） |

> **结论：上游没有自动化测试入口，上游用例总数为 0。**
> 所有上游样例（`testbios.c`、`lfbprof`）均已定位并逐一实测其可执行性，
> 无漏测；`test_package` 结果不计入本表（见下）。

---

## 二、消费者侧测试（test_package，实质消费被测包）

- **入口**：`test_package/test_vgabios.sh`（由 `test_package/conanfile.py` 的 `test()` 调用）
- **断言助手**：`test_package/verify_rom.py`
- **被测包**：`vgabios/0.8a`（`<package>/share/vgabios/*.bin` 与 `<package>/bin/biossums`）
- **运行命令**：

```bash
bash test_package/test_vgabios.sh <package_folder>
# conan create 中由 test_package/conanfile.py 自动调用：
#   self.run(f'{bash} "{script}" "{pkg}"')
```

**本次运行**（包目录 `/storage/Users/currentUser/.conan2/p/b/vgabid763ddd24eefc/p`）：

```
CASE SUMMARY: total=9 passed=9 failed=0 skipped=0
RESULT: PASS
```

日志：`reports/test-package-run.log`（完整逐例输出）；
conan create 侧日志：`reports/conan-create.log`。

### 2.1 测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总用例数 | 9 | 100% |
| 通过 (PASS) | 9 | **100%** |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |
| **其中鸿蒙平台专有用例** | **1**（`TC-09-ohos-host-abi`） | — |

### 2.2 逐项用例明细

| # | 用例名称 | 测试内容 | 结果 |
|---|----------|----------|:----:|
| 1 | `TC-01-rom-inventory` | 5 个 ROM 镜像齐备且尺寸与 0.8a 基线一致（38400/39424/33280/33280/32768 B） | ✅ PASS |
| 2 | `TC-02-rom-signature` | 每个 ROM 偏移 0 处为 x86 Option ROM 签名 `0x55AA` | ✅ PASS |
| 3 | `TC-03-rom-checksum` | 每个 ROM 前 `data[2]×512` 字节求和 ≡ 0 (mod 256)（biossums 写入） | ✅ PASS |
| 4 | `TC-04-rom-sizefield` | 每个 ROM 的长度字段 `data[2]×512` == 文件大小 | ✅ PASS |
| 5 | `TC-05-pci-structure` | 每个 ROM 的 PCIR 结构：指针 `@0x18` == 0x0110、magic `PCIR`、Vendor ID / Device ID / Image Length 全部匹配（0x1234:0x1111 / 0x1013:0x00B8 / 0x121A:0x0003） | ✅ PASS |
| 6 | `TC-06-rom-ident` | 偏移 `0x1e` 处 `IBM` 标识 + 包内 `Bochs VGABios` 版本串 | ✅ PASS |
| 7 | `TC-07-variant-tags` | cirrus 变体串、banshee 变体串（`VGABIOS Banshee extension` / `3dfx Voodoo`）、debug 变体 DEBUG 串（`--> Unknown int10` / `vgabios cirrus call`）与 release 变体区分 | ✅ PASS |
| 8 | `TC-08-biossums-fix` | 破坏 ROM 载荷字节（0x2000）后实际运行包内 `bin/biossums`：退出码 0、校验和被修复、载荷字节保留（38400 → 38912，追加校验页） | ✅ PASS |
| 9 | `TC-09-ohos-host-abi` | **【鸿蒙特有】**`bin/biossums` 为 ELF64 / little-endian / AArch64（OHOS 目标）且可在本机（HarmonyOS aarch64）实际执行 | ✅ PASS |

### 2.3 鸿蒙特有测试说明（数量 = 1 ≥ 1）

`TC-09-ohos-host-abi` 断言包内 `bin/biossums` 的 ELF 头为
`ELF64 + little-endian + e_machine=0xB7(AArch64)`，并在 HarmonyOS 宿主机上
**实际执行**（对包内 banshee ROM 跑一次校验和检查，退出码 0）。
这是本包唯一依赖平台的目标产物（ROM 本身为与宿主无关的 8086 固件），
故以该原生可执行文件承载鸿蒙平台专有断言。

---

## 三、门禁与日志索引

| 门禁 | 结果 | 日志/证据 |
|------|:----:|-----------|
| `conan create`（含 test_package） | ✅ 退出码 0 | `reports/conan-create.log` |
| `conan-verify`（G0–G4 + L2/L4/L5） | ✅ PASS | `reports/conan-verify-report.md` |
| `finish`（含 W2/W3） | ✅ `status: built`（W3 本地 CI 模拟通过） | `reports/w3-local-ci.log` |
| 上游测试入口核验 | ✅ 已核验（无自动化测试） | `reports/upstream-check.log` |
| 消费者侧测试 | ✅ 9/9 PASS（含 1 项鸿蒙特有） | `reports/test-package-run.log` |
