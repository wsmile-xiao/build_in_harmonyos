# binutils 2.46.0 HarmonyOS PC 未通过项分析

## 证据身份

- 最终 clean run：`final-build39`，Conan create 退出码 0。
- 输入 bundle SHA256：`61f2ab642e0405787a1af1fa34e47b9e12281eb9fd1d8a93d509348fc2beec79`。
- 回传归档 SHA256：`8efd26e9be91e44d4deb7eb53a4d85ebc9320dc54481f00d392936b183d7c6f3`。
- 结果清单：138 个文件逐项通过大小和 SHA256 校验。
- DejaGNU：3419 PASS / 35 FAIL / 0 UNRESOLVED，普通通过率 98.99%。
- 归因检查：分类器完成 35/35 名称映射；结合日志上下文和对照试验复核，未发现当前
  适配引入的失败。

## 逐项清单

| # | 套件 | 未通过测试 | 类别 |
|---:|---|---|---|
| 1 | binutils | `gnu-debuglink (objdump 1)` | C01 |
| 2 | ld | `Build dt-relr-glibc-1b.so` | C02 |
| 3 | ld | `DWARF parse during linker error` | C03 |
| 4 | ld | `preinit array` | C04 |
| 5 | ld | `PIE preinit array` | C04 |
| 6 | ld | `Static PIE preinit array` | C04 |
| 7 | ld | `static preinit array` | C04 |
| 8 | ld | `Run with libindirect4c.so 1` | C05 |
| 9 | ld | `Run with libindirect4c.so 2` | C05 |
| 10 | ld | `Run with libindirect4c.so 3` | C05 |
| 11 | ld | `Run with libindirect4c.so 4` | C05 |
| 12 | ld | `Build warn libbar.so` | C06 |
| 13 | ld | `Build libpr19073.so` | C07 |
| 14 | ld | `Dump pr21978.so` | C08 |
| 15 | ld | `Run normal with versioned libfoo.so` | C09 |
| 16 | ld | `Run warn with versioned libfoo.so` | C06 |
| 17 | ld | `Run protected with versioned libfoo.so` | C09 |
| 18 | ld | `Run normal libbar.so with versioned libfoo.so` | C09 |
| 19 | ld | `Run protected libbar.so with versioned libfoo.so` | C09 |
| 20 | ld | `Run relmain` | C10 |
| 21 | ld | `Run pr2404` | C11 |
| 22 | ld | `Run pr2404n` | C11 |
| 23 | ld | `Run with libnew1a.so` | C12 |
| 24 | ld | `Run with libnew1b.so` | C12 |
| 25 | ld | `Run pr2404 with PIE` | C11 |
| 26 | ld | `Run pr2404 with PIE (-z now)` | C11 |
| 27 | ld | `Run pr19579` | C13 |
| 28 | ld | `Run pr19579 (-z now)` | C13 |
| 29 | ld | `pr22263-1 -z text` | C14 |
| 30 | ld | `Run pr33577a ... --as-needed,--hash-style=sysv` | C15 |
| 31 | ld | `Run pr33577a ... --as-needed,--hash-style=both` | C15 |
| 32 | ld | `Run pr33577a ... --no-as-needed,--hash-style=sysv` | C15 |
| 33 | ld | `Run pr33577a ... --no-as-needed,--hash-style=both` | C15 |
| 34 | ld | `Run pr33577a ... --as-needed,--hash-style=gnu` | C15 |
| 35 | ld | `Run pr33577a ... --no-as-needed,--hash-style=gnu` | C15 |

## 根因与对照证明

| 类别 | 数量 | 根因、对照与影响 |
|---|---:|---|
| C01 | 1 | 原始和 strip 后反汇编仅操作数的符号注释不同：`_DYNAMIC+...` 与 `.got.plt+...`；指令字节一致，压缩/解压 debuglink 两份 dump 互相一致。只影响一项 objdump 展示比较。 |
| C02 | 1 | 用例要求 `.gnu.version_r` 中出现 glibc 的 `GLIBC_ABI_DT_RELR`；OHOS 使用 musl `libc.so`，文件不携带 GLIBC 版本需求。DT_RELR 链接本身成功。 |
| C03 | 1 | GNU ld 正确拒绝两处重复定义，但 OHOS Clang 调试信息只让它输出节偏移，未输出用例要求的源码行号；同一用例在 WSL Clang 基线也失败。只影响诊断文本。 |
| C04 | 4 | `runtime19` 用完全相同源码分别经 SDK LLD 和 GNU ld 链接并签名。GNU ELF 保留含 3 个入口的 24 字节 `.preinit_array`，两种链接器产物运行都为 rc=0、空输出，定位为 OHOS loader 行为。 |
| C05 | 4 | `runtime24` 将三个上游翻译单元按完整套件的 `-O3` 分别编译，SDK LLD 与 GNU ld 产物都输出 `MAIN2/DSO`，而用例要求 `MAIN2/MAIN2`。定位为 Clang O3 符号插桩优化，与链接器选择无关。 |
| C06 | 2 | GNU ld 已发出弃用警告，但位置为 `.init_array+0x0`；用例严格要求 `beginwarn.c:7`。两个测试均在 WSL Clang 基线失败，只影响精确诊断位置。 |
| C07 | 1 | OHOS Clang 集成汇编器对 `.weak` 绑定变化输出警告，DejaGNU 因非空编译输出将前置对象标为 UNSUPPORTED，随后产生一个级联 FAIL；GNU ld 尚未参与。WSL Clang 基线相同。 |
| C08 | 1 | `runtime41` 分别用默认 DWARF 和 `-gdwarf-4` 重建测试对象。两次都能解析 `foo/bar` 源码行，但链接进来的 OHOS SDK CRT 行表都产生相同 8 条错误，定位为 SDK CRT 调试信息互操作。 |
| C09 | 4 | 四个签名程序均 rc=0，但 OHOS musl loader 在版本化 DSO 组合中先解析到 `TEST2`，用例要求 `TEST1`。链接、签名和执行均已成功。 |
| C10 | 1 | `librel.so` 的 `__start_auto/__stop_auto` 在最终可执行文件链接时未隐式解析；相同 `Run relmain` 在 WSL Clang 基线也失败，属于上游基线场景。 |
| C11 | 4 | `runtime19` 用 SDK LLD 与 GNU ld 构建相同 `times` 数据符号碰撞源码；两者都输出 `times: -1` 后 SIGSEGV，定位为 OHOS libc 名称碰撞行为。 |
| C12 | 2 | `runtime33` 保持上游编译/链接标志，仅把隐藏计数打印出来；两个变体都是 `pass=489`，而 libstdc++ 用例固定期望 4。WSL libc++ 基线也失败。 |
| C13 | 2 | `runtime41` 使用同一组 `-fPIE/-fcommon` 对象：SDK LLD 链接 rc=0；GNU ld 在 `-pie -z text` 下拒绝可外部绑定的 `R_AARCH64_ADR_PREL_PG_HI21`。这是 GNU ld 的 AArch64 PIE copy-relocation 行为。 |
| C14 | 1 | OHOS Clang 将 TLS 降级为 `__emutls_get_address`；该上游用例直接调用 ld 且使用 `-nostdlib`，未链接 compiler runtime。普通 compiler-driver 消费路径已通过。 |
| C15 | 6 | 最终套件的六种 as-needed/hash-style 组合均在无版本 DSO 阶段通过，替换成版本 DSO 后 rc=0、空输出。`runtime19` 另以一种代表性配置按相同流程对照 SDK LLD 与 GNU ld，两者都复现替换后的空输出，定位为 OHOS musl 的无版本符号绑定规则。 |

## 预期失败、未测试和排除项

- 15 个 XFAIL 是上游预先标记的预期失败，不计入普通 PASS：binutils 2 项，ld 13 项。
- 203 个 UNSUPPORTED 主要是非 aarch64 目标、big-endian/32-bit 变体、IFUNC/x86 场景、
  编译器无 CTF、缺 debuginfod 等能力探测结果；它们不被重标为 PASS。
- 4 个 UNTESTED 为 `readelf -wi`、`readelf -wa (compressed)`、
  `bootstrap with --static`、`PR ld/33401`。前两项由 Clang 在 `-c` 阶段报告 linker-only
  参数未使用；静态 bootstrap 缺目标静态启动闭包；PR 33401 的 AArch64 `.rela.sframe`
  没有用例所需的 `R_*_NONE` 占位项。
- gprof 上游发现 2 个 shell 测试，但配置探针得到 `gprof_cv_sys_native=no`，设备实际
  0 discovered / 0 executed，未写成通过；安装包中的 `gprof --version` 仍通过。
- gprofng 的 7 个 `.exp` 随 Linux 专用 collector 组件显式关闭，不进入分母。

## 适配缺陷排除过程

`final20` 为 3393 PASS / 60 FAIL。诊断发现两项实际适配缺陷：压缩调试用例未让
Clang 使用本轮 GNU as，以及 `pr21964-2b.so` 作为 literal `dlopen` 输入漏签。修复后，
过宽的外部汇编器试验 `final34` 又新增 `mbind2a/b` 两项，归因门禁将其判为适配缺陷并
拒绝。最终 `0025` 仅在 `compress.exp` 内启用并恢复外部 as，`final39` 同时满足：

- 压缩调试 28/28 PASS；
- `pr21964-2` PASS；
- `mbind2a/b` 恢复为基线的 UNSUPPORTED，未形成 FAIL；
- 35 个剩余 FAIL 全部归因，未发现由当前适配补丁引入的失败。
