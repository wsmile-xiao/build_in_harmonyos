# DRAFT-lazarus-4.8-fpc-rtl-glibc-startup-and-interp

> **Contributor**: staralsnow | **Status**: DRAFT | **Updated**: 2026-09-29
> **Severity**: 🟠 high（构建全绿但产物不可执行） | **Category**: toolchain / linking / runtime / portability
> **Source**: task #8032 `lazarus@4.8` 适配（2026-09-29）

## 使用说明（何时用）

当**为 Linux/glibc 目标设计的启动对象**（`crt1.o` 族，FPC 里叫 `cprt0.o`）被搬到 OHOS/musl 上，
且你看到下面任一条时：

- 链接期：`ld.lld: error: undefined symbol: __libc_csu_init`（或 `__libc_csu_fini`）；
- 运行期：`Could not open '/lib/ld-linux-aarch64.so.1': No such file or directory`；
- `readelf -x .interp <exe>` 显示的是 `ld-linux` 而不是 `ld-musl`。

处理顺序固定：

1. **补启动符号**：用目标平台编译器汇编一份空的 `__libc_csu_init`/`__libc_csu_fini`，编成 `.o` 后链入（FPC 用 `-k<shim.o>`）；
2. **改解释器**：在打包阶段对每个交付 ELF 就地等长改写 `.interp`：`/lib/ld-linux-aarch64.so.1\0`（26B）→ `/lib/ld-musl-aarch64.so.1\0` + 1B 补零（25B），文件长度不变；
3. 不要指望 `-k--dynamic-linker=`：本案例实测该参数不改变产物 `.interp`。

## 适用范围

**适用**：

- FPC RTL 的 `cprt0`/`crt1` 族，即一切 `tool_requires(fpc/...)` 的消费者（本案例是 lazarus/4.8）；
- 其它语言/运行时自带的 `_start` 与 `crt` 对象（只要引用了 glibc 专有 `__libc_csu_*`）；
- 直接搬运的 Linux 预编译 ELF（其 `.interp` 指向 `ld-linux`）。

**不适用 / 边界**：

- 库级链接期缺 glibc 扩展符号（如 `feenableexcept`）——那是另一类，见 `DRAFT-lfortran-runtime-ohos-adaptation`；
- 目标本就带正确 musl 解释器与 musl 启动对象的产物（无需处理）；
- 若改用 `patchelf --set-interpreter` 会改变文件布局、需重新签名，OHOS worker 不保证有 patchelf，故默认走等长原地替换。

## 输入输出定义

**输入**：

- 一个已链接、但 `.interp` 指向 `ld-linux`（或链接期缺 `__libc_csu_*`）的 aarch64 ELF；
- OHOS 的 clang（生成 aarch64 汇编 shim）；
- 目标平台 musl loader 路径常量：`/lib/ld-musl-aarch64.so.1`。

**输出**：

- 同一文件、同一长度的 ELF：`.interp` = `/lib/ld-musl-aarch64.so.1`，可在 OHOS 上执行；
- 启动符号由空 shim 提供（本案例 FPC 的 `_start` 不依赖其做实际初始化）。

**判定**：`readelf -x .interp <exe>` 命中 `ld-musl-aarch64`，且 `<exe>` 直接执行成功。

## 示例（本案例实测）

```sh
# 1) 链接期症状（未打补丁）
$HOME/.conan2/p/b/fpc*/p/lib/fpc/3.2.2/ppca64 ... -k--dynamic-linker=/lib/ld-musl-aarch64.so.1 ...
#   → ld.lld: error: undefined symbol: __libc_csu_init

# 2) 补 shim 后：链接通过，但 .interp 仍是 ld-linux
$ readelf -x .interp test/runtests
#   0x...  2f6c6962 2f6c642d 6c696e75 782d6161  /lib/ld-linux-aa
#   ...    1 -> /lib/ld-linux-aarch64.so.1
$ ./runtests --suite=TTestLazUtils
#   aarch64-binfmt-P: Could not open '/lib/ld-linux-aarch64.so.1': No such file or directory

# 3) 等长改写 .interp 后
$ readelf -x .interp test/runtests
#   ... -> /lib/ld-musl-aarch64.so.1
$ ./runtests --suite=TTestLazUtils --format=plainnotiming
#   Number of run tests: 4   errors: 0   failures: 0   (EXIT=0)
```

## 查重差异表（与最相近条目逐条比）

| 维度 | DRAFT-lfortran-runtime-ohos-adaptation | 本条目 |
|---|---|---|
| 触发阶段 | 库编译/链接（`-shared` 允许未定义符号） | 可执行文件**启动**（启动对象 + `.interp`） |
| 签名 | `call to undeclared function 'feenableexcept'` / `undefined symbol: feenableexcept` | `undefined symbol: __libc_csu_init` / `Could not open '/lib/ld-linux-aarch64.so.1'` |
| 根因 | glibc 扩展函数在 musl 缺实现 | glibc 专有启动符号 + 写死的 ELF 解释器路径 |
| 修法 | 源码层 FPCR 直写替代（可选 shim 回退） | 汇编空 shim + 打包期**等长就地改写 `.interp`** |
| 关键坑 | 把「`-shared` 链接成功」当适配完成 | 把「链接成功/CI 绿」当适配完成（产物仍不可执行） |

`similar_to`: `DRAFT-lfortran-runtime-ohos-adaptation`、`E2175`。

## 验证证据

| 步骤 | 命令 | 结果 |
|---|---|---|
| musl 不提供 `__libc_csu_*` | `llvm-nm -D --defined-only <sysroot>/usr/lib/aarch64-linux-ohos/libc.so \| grep -c __libc_csu` | `0` |
| 未打补丁链接 | `ppca64 ...` | `ld.lld: error: undefined symbol: __libc_csu_init`（FAIL，见 build 日志） |
| 补 shim 后运行 | `./runtests --suite=TTestLazUtils` | `Could not open '/lib/ld-linux-aarch64.so.1'`（EXIT=255） |
| 改写 `.interp` 后 | `readelf -x .interp` + `./runtests ...` | `ld-musl-aarch64`；48 项实跑（41 通过 / 3 失败 / 4 错误） |

证据日志（绝对路径）：

- `tasks/lazarus-4.8-2026-09-25/logs/091-upstream-runtests-build.log`（`runtests` 编译，EXIT=0）
- `tasks/lazarus-4.8-2026-09-25/logs/092-upstream-runtests-unit-subset.log`（逐 suite 明细）
- `tasks/lazarus-4.8-2026-09-25/logs/090-upstream-runtests-list.log`（上游 406 用例 / 353 suite 清单）

## 平台侧修法建议（若有）

- 若 OHOS 未来提供 `ld-linux` 兼容符号链接，则第 2 步可省；在此之前，**等长改写 `.interp`** 是最小侵入做法（不重链接、不改布局、不改签名时机）。
- 建议在 CI 的 L0/L1 里补一条「产物可执行性」检查（`readelf -x .interp` 必须命中 `ld-musl`），可一次性拦住这一类「构建绿但跑不起来」的假阳性。
