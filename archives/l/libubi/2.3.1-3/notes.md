# libubi 2.3.1-3 适配笔记

> libubi 是 mtd-utils 2.3.1 内的 UBI（Unsorted Block Images）开发库。Debian/Ubuntu 源包
> `mtd-utils 2.3.1-3` 编出 `libubi-dev` 二进制包，其产物（libubi.a、libmtd.a、公共头文件、
> mtd/ 内核 UAPI 头）正是本配方打包内容。上游源码为 `mtd-utils-2.3.1`。

## 编译环境

- 目标平台: OpenHarmony / HarmonyOS PC (aarch64, triplet `aarch64-linux-ohos`)
- 构建系统: 直接编译器调用（direct-cc）+ 一次 `./configure` 仅用于生成 `include/config.h`
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`），归档器 llvm-ar（`/data/service/hnp/bin/llvm-ar`）
- 签名工具: llvm-readelf / binary-sign-tool
- 编译日期: 2026-09-29
- 状态: built（conan-verify G0-G4 + L2/L4/L5 全通过，未 upload）

## 选型依据（为什么不用完整 autotools 构建）

1. **config.h 必需**：lib/ 下源码全部带 `-include config.h`，且 `lib/execinfo.c` 用
   `HAVE_EXECINFO_H` 分支 —— 必须先 `./configure` 生成 `include/config.h`。
2. **noinst_LIBRARIES 缺口**：上游把这些 lib 声明为 `noinst_LIBRARIES`，`make install` 不安装它们。
   若走 `make install` 会拿不到 .a / 头文件。因此改为手动 `make <lib>.a` 后自行安装。
3. **safe-bin 陷阱**：OHOS 沙箱 PATH 前端 `safe-bin/rm`、`safe-bin/sh` 的 shebang 是
   `#!/bin/bash`（OHOS 不存在），会让 `./configure`/`make` 中途 `Exec format error` 失败；
   必须前置 `PATH=/system/bin:$PATH` 并显式传 `RM/SHELL/MKDIR_P` 覆盖。
4. **代价最小**：libubi 自包含（仅依赖 libc，`llvm-nm` 确认无外部未定义符号、不依赖 libmtd），
   把 6 个静态归档抽取 .o 后合并为单一 `libubi.a`，消费者 `-lubi` 一次拉齐整库。
   静态库优先（R4/R26 一致，且上游本就不产出 .so）。

## 编译步骤

1. `source()` 拉取并校验上游 `mtd-utils-2.3.1.tar.bz2`（sha256 不符即失败）
2. `build()` 先 `export TMPDIR` 指向可写目录（OHOS 上 `/tmp` 只读），否则 clang 临时文件失败
3. **仅生成 config.h**：`sh ./configure CC=clang --prefix=/ --without-zlib --with-lzo=no
   --with-zstd=no --with-selinux=no --without-crypto --without-ubifs --without-jffs
   --without-xattr --without-tests --disable-unit-tests --without-lsmtd
   --disable-ubihealthd RM=/system/bin/rm SHELL=/system/bin/sh MKDIR_P='/system/bin/mkdir -p'`，
   命令前置 `export PATH=/system/bin:$PATH`
4. 顶层 Makefile 非递归，直接 `make libmtd.a libmissing.a libubi.a libubigen.a libscan.a
   libiniparser.a`（注意 target 名是顶层 `libmtd.a`，不是 `lib/libmtd.a`）
5. 用 llvm-ar 把 6 个 .a 的 .o 抽取到临时 objs 目录，再 `llvm-ar rcs libubi.a *.o` 合并为
   单一自包含 `libubi.a`（落在 build_folder，不污染源码树）
6. `package()`：复制 `include/*.h`（`keep_path=True`，含 `mtd/` 子目录 UAPI 头，排除
   `config.h`）、`COPYING`→licenses、`libubi.a`→lib；`package_info().libs=["ubi"]`
7. test_package：用校验过的 clang 直接编译 `test_package.c` 链接 `libubi.a`，OHOS 平台
   `binary-sign-tool sign` 自签并断言 `.codesign` 段恰为 1 个后运行；要求 rc=0 且 ≥4 条
   `CHECK ... OK` 行（`libubi_open` 在无设备主机返回 NULL 符合文档行为、`struct ubi_mkvol_request`
   公共 API 可用、`libubi_close(NULL)` 不崩溃、完成标记），并显式 `self.run(executable,
   env="conanrun")` 满足 L0 stub 门禁；输出 `HMBS_TEST_PACKAGE_RESULT=...`

## 上游测试清点（R51 申报表）

| 来源 | 发现方式 | 用例数 |
|------|---------|--------|
| autotools `make check` | 上游测试套件通过 `--without-tests` 关闭 | 0（本包不跑） |
| 安装后消费者端到端 | test_package.c（真实公共 API 工作流） | 1 流程 / 4 个 CHECK 断言 |

- 本包为纯库，不含可独立执行的上游自测程序；端到端消费者流程为 1 条、4 个断言共享同一进程命运。
- 反例空输出（无任何 CHECK 行）会被 `len(checks) < 4` 判为失败，证明判定非空转。

## 验证结果

```bash
# 1) 八道门禁
ohc-run.py conan-verify libubi 2.3.1-3
# G0 PASS / G1 PASS / G2 PASS / G3 PASS / G4 PASS / L2 PASS / L4 PASS / L5 PASS

# 2) 安装后消费者端到端（test_package）
[CHECK libubi_open OK] returned NULL (no /dev/ubi_ctrl, expected)
[CHECK struct_api OK] ubi_mkvol_request name=libubi-test bytes=1024
[CHECK close_null OK] libubi_close(NULL) did not crash
[CHECK consumer_complete OK] libubi dev library usable as a consumer
TESTS PASSED
HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"discovered":1,"passedCount":1}
```

- 端到端消费者流程通过率：**1/1（100%，含 4 个 CHECK 断言）**

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `./configure` 中途 `could not create tests/fs-tests/fs_help_all.sh` | 沙箱 PATH 前端 `safe-bin/rm`、`safe-bin/sh` 为 `#!/bin/bash` 死链（OHOS 无 `/bin/bash`） | 命令前置 `export PATH=/system/bin:$PATH`，并显式传 `RM=/system/bin/rm SHELL=/system/bin/sh MKDIR_P='/system/bin/mkdir -p'` |
| 2 | `make lib/libmtd.a` 报 `No rule to make target` | 顶层 Makefile 非递归，target 名为 `libmtd.a` 而非 `lib/libmtd.a` | 改用 `make libmtd.a libmissing.a libubi.a libubigen.a libscan.a libiniparser.a` |
| 3 | `unable to open output file '/tmp/libubi.o': Read-only file system` | OHOS 上 `/tmp` 只读 | 改用可写 build 目录（`_ensure_writable_tmp` 把 TMPDIR/TMP/TEMP 指向 build_folder/hmbs-tmp） |
| 4 | `/system/bin/ar` 不存在、toybox 无 ar | 系统归档器缺失 | 改用 `/data/service/hnp/bin/llvm-ar`（`llvm-ar rcs/x` 验证可用） |
| 5 | OHOS 运行测试二进制 `Permission denied` | 鸿蒙 PC 要求 ELF 带 `.codesign` 段 | test_package 用 `binary-sign-tool sign` 自签，并断言 `.codesign` 段恰 1 个 |

## 源码修改

无。上游 `mtd-utils-2.3.1` 源码未经任何修改（`refresh-patch` 无补丁产出），因此不引入 `patches/`。

## 依赖版本

无第三方依赖（纯 libc）。UPX 可选但已 `--without-...` 全部关闭。

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/libubi.a` | 静态库（6 个上游归档合并后的自包含单体） |
| `include/libubi.h`、`include/libmtd.h`、`include/libubigen.h`、`include/libscan.h`、`include/libiniparser.h` | 上游公共头文件原样安装 |
| `include/mtd/*.h` | 上游内核 UAPI 头（消费者 `#include <mtd/ubi-user.h>` 等需要） |
| `licenses/COPYING` | 上游 GPL-2.0-or-later 许可文本 |

## 注意事项

- libubi 自包含（仅 libc），合并后的 `libubi.a` 不依赖 libmtd，消费者 `-lubi` 一次拉齐。
- 本配方只产出静态库，不产出 `.so`，因此无 SONAME 质量门要求（R4/R26 静态优先，与上游一致）。
- 修改 ELF 会破坏自签、被鸿蒙 PC 的 XPM 拒绝 dlopen；测试二进制在链接期生成后即整体签名，不做事后 patchelf。
---
**编译结束**: 2026-09-29
**最终状态**: built
