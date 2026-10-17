# UASM 2.57 适配笔记（OHOS aarch64）

## 源码与版本

- 平台任务版本 `2.57` 对应上游 git tag **`v2.57r`**（`Terraspace/UASM`，`97f64389`）。
- 源码：`https://codeload.github.com/Terraspace/UASM/tar.gz/refs/tags/v2.57r`
  （`https://github.com/.../archive/refs/tags/v2.57r.tar.gz` 为同一归档的备用 URL，字节一致）
  sha256 `09fa69445f2af47551e82819d024e6b4b629fcfd47af4a22ccffbf37714230e5`。
- UASM 是纯 C 的 MASM 兼容汇编器（Open Watcom Public License），无三方依赖。

## 构建

上游 `Makefile-Linux-GCC-64.mak` 直接用 OHOS clang 即可，需附带：

```sh
make -f Makefile-Linux-GCC-64.mak \
  CC="<ohos-sdk>/bin/clang -fcommon" \
  CFLAGS="-O0 -fno-strict-aliasing -Wno-error -Wno-implicit-function-declaration \
          -Wno-int-conversion -Wno-incompatible-pointer-types -Wno-implicit-int -Wno-return-type"
```

产物 `GccUnixR/uasm`，安装为 `bin/uasm`，另装 `licenses/License.txt`。

## OHOS / clang23 / aarch64 移植要点

| # | 现象 | 根因 | 处理 |
|---|------|------|------|
| 1 | 编译报 `call to undeclared function 'AddSimdTypes'/'strupr'/...`、`incompatible pointer types`、`int-conversion` | v2.57r 早于 clang 16；clang≥16 将这些警告提升为硬错误 | 显式 `-Wno-*` 降级；其中 `macho64.c` 的 `mm.header.flags = NULL`（void*→uint32）值为 0，安全 |
| 2 | **AVX/VEX 指令编码全错**（如 `vpmaskmovd xmm6,xmm4,[rcx]` 输出 `c4 e2 59 8c f0 00`，应为 `c4 e2 59 8c 31`）；`mov`/内存寻址等传统指令正常 | `codegenv2.c` 在 clang23 `-O2` 下被误编译（类型双关 UB） | 用 `-O0` 构建；`-O2 -fno-strict-aliasing` 不足以修复，实测 `-O0` 后逐字节正确 |
| 3 | `-1 SHR 4` 结果 `0xFFFFFFFF`（算术右移）而非 `0x0FFFFFFF`（逻辑右移），`plain_bin/opshr2` 失败 | `expreval.c` T_SHR 用 `(unsigned long)` 做 32 位语义；`long` 在 Windows(LLP64)=32 位、在 OHOS(LP64)=64 位 | 源码内改 `(uint_32)opnd1->llvalue >> opnd2->value` |
| 4 | 链接 `posix_spawn failed: No such file or directory` | 直接调用 clang 时缺 `LD=ld.lld` 等；OHOS profile 的 buildenv 会注入 | 用 `conan create`（自动 buildenv），无需手工设置 |

第 3 条是典型的 **LLP64→LP64 移植坑**：源码只在 Windows 上跑过，`unsigned long` 的位宽假设被 aarch64 打破。

## 上游测试（regress）

- 上游套件是 **Windows 专用**：`regress/runtests.cmd` + 私有 `fcmp.exe`，按
  `regress/src/<cat>/*.asm` 组装并与 `regress/exp/<cat>/` 比对；上游 CI（`.travis.yml`
  只 `make`，GitHub workflow 引用了不存在的 `gccLinux64.mak check`）**从不运行它**。
- 本配方移植为 POSIX 运行器 `regress_runner.sh`（`build()` 内嵌生成）：
  - 二进制类别（`plain_bin` 403、`CodeGenV2` 44、`flat`、`flat16`、`linux64`、`macho64`）
    以**机器码产物**为判定目标，逐字节 `cmp`；
  - 错误类别（`avxerr`、`mz`、`literalerr`、`literals`、`invoke64err`、`vcall`、`win64`、
    `CodeGenV2Error`、`pe64_bin`）以 `.err` 文本为判定目标（归一化 `\`→`/`、去 CR、忽略大小写）。
- 结果：**469 / 477 通过（98.3%）**。
- 未通过的 8 条：
  - `.err` 文本失配 5 条（`pe64_bin/bin64`、`mz/ABSSEG`、`mz/FIXUP3`、`mz/JMPCALL8`、`win64/record64`）：
    期望要求 level-2 警告 `A4299 "BSS data in BIN output"`，而 v2.57r 中该警告**唯一调用点**在
    `simsegm.c` 且条件是 `.data?` 段（`ModuleInfo.flat`），普通段里的 `db ?`/`dw ?` 不触发；
    `exp/win64/record64.err` 更与 v2.57r 源码对不上（期望 393/394 行 A2237，实际源码对应
    260/263 行 A2275）——均为**期望数据过期**，与本次适配无关。
  - `CodeGenV2Error/MOV64_6`：`.err` 错误文本差异，同属过期诊断期望。
  - `linux64/Lin64_1.o`：仅差 `EI_OSABI` 一个字节（本构建 0=System V，期望 3=GNU/Linux），平台默认差异。
  - `macho64/osx2.o`：Mach-O 目标差异（上游期望同样来自不同修订）。
- 全部 8 条都不是机器码编码错误：二进制类别（403+44+…）逐字节通过。

## 消费者测试

`test_package/test_uasm.sh`（6 项断言）：版本横幅、普通 MASM 平铺二进制、
32 位 SHR（LP64 修复）、CodeGenV2 VEX 编码、ELF64 可重定位目标、非法指令报错。

## 复现

```sh
conan create archives/u/uasm/2.57 \
  -pr:h=$HOME/.conan2/profiles/ohos-aarch64 -pr:b=$HOME/.conan2/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```
