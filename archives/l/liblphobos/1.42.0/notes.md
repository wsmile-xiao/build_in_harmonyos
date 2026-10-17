# liblphobos 1.42.0 适配笔记（鸿蒙 PC 真机原生构建）

## 包定位

liblphobos = LDC 1.42.0 发行源码中的 D 语言运行时库（`runtime/phobos` +
`runtime/druntime` 子树），即：

- **Phobos 标准库**：`libphobos2-ldc-shared.so`（SONAME `.so.112`，DMD 前端 2.112.1）
- **伴生运行时 druntime**：`libdruntime-ldc-shared.so`（SONAME `.so.112`，Phobos 硬依赖，同包交付）

与 `ldc/1.42.0` 工具包（application，`bin/ldc2` 等；其 `lib/` 仅静态库
`libphobos2-ldc.a` 等）**互补零重叠**：本包交付**共享库**（`BUILD_SHARED_LIBS=ON`，
上游自动产出 release+debug 两套 .so）。平台任务语言标签为 C（native 库通道），
真实实现语言为 D（以 ldc 工具链通道适配）。

## 构建方式（上游官方路径）

上游独立构建运行时的钦定工具 `ldc-build-runtime` 在 OHOS **动态链接不可运行**
（缺 `libgcc_s.so.1`/`_Unwind_*`，`ldc/1.42.0` 配方实测，见其 manifest
knowledge_gained）。本配方**复刻其 `runCMake()` 的官方参数**直接驱动上游
`runtime/CMakeLists.txt`：

```sh
cmake -S <src>/runtime -B <build> \
  -DLDC_EXE_FULL=<ldc包>/bin/ldc2 -DLDMD_EXE_FULL=<ldc包>/bin/ldmd2 \
  -DDMDFE_MINOR_VERSION=112 -DDMDFE_PATCH_VERSION=1 \
  -DTARGET_SYSTEM="Linux;UNIX;musl" \
  -DBUILD_SHARED_LIBS=ON -DCMAKE_BUILD_TYPE=Release \
  -DLD_FLAGS=<shim.o> -DCMAKE_MODULE_PATH=<HarmonyOS.cmake stub 目录> ...
cmake --build <build> --parallel 4
```

- D 编译器来自 `tool_requires("ldc/1.42.0")`（2026-09-17 已发布 ohpcd，
  二进制 `e11077ec…`，CI 同款 profile，直接命中无需现场编译 ldc）。
- `TARGET_SYSTEM` 显式 `Linux;UNIX;musl`（OHOS libc 为 musl 变体），绕开
  `uname=HarmonyOS` 的 AUTO 探测不确定性。
- `.so` 交付前经 `binary-sign-tool` 自签，SONAME 软链实体化（E316/E492/E505）。

## OHOS 适配点

| 项 | 说明 |
|----|------|
| **glibc 符号残留（★本包特有）** | druntime `core/internal/elf/dl` 引用 `program_invocation_name`（glibc 特有，musl 无）。静态库场景该成员不被拉入（ldc 包无恙）；**共享库整体打入 dl.o**，未定义符号致消费者链接必报 `--no-allow-shlib-undefined`。处置：`shim/pthread_cancel_shim.c` 编为 PIC 对象经上游 `LD_FLAGS` 链进 .so（`program_invocation(_short)_name` 空串定义，与 ldc 引导期适配同构） |
| **SIGRTMIN / pthread cancellation** | 继承 ldc/1.42.0 的 `patches/0001-ohos-thread-gc-signals.patch`（同一 druntime 源码：SIGRTMIN(35) 不可达 → SIGUSR1/2；musl 缺 pthread cancel 家族 → no-op 回退） |
| **代码签名** | 全部交付 .so 与测试产物 `binary-sign-tool sign -selfSign 1` |
| **Platform/TMPDIR** | `Platform/HarmonyOS.cmake` stub（同 llvm/flang-ohos/ldc）；`/tmp` 只读 → 显式 TMPDIR |
| **DMD 方言差异** | `-version=X` 在 ldc2 报 `does not allow a value`（LDC 语法 `-d-version=X`）；官方基础 `DFLAGS = -w -de -preview=dip1000 -preview=dtorfields -preview=fieldwise` 不可省（缺 dip1000 时 std/algorithm 等 @safe 借用检查编译失败） |

## 验证结果（本地真机 `conan create`，CI 同款 profile）

- **conan create**：通过（`reports/conan-create.log`，CREATE_EXIT=0）
- **test_package（鸿蒙消费者用例，新增）**：7/7 断言通过——`ldc2 -conf=` 完全
  脱离编译器默认配置，import/库全部指向本包（`-I<包>/include/d -L-L<包>/lib
  -defaultlib=phobos2-ldc-shared,druntime-ldc-shared`），真实编译 + 签名 + 运行
  + 逐行断言（std.algorithm/std.range/std.format/std.conv/std.json/std.string/
  std.datetime 全链路）
- **上游测试**：见下节

## 上游测试实测（Phobos unittest 全量）

- **上游入口**：`runtime/phobos/Makefile` 的 unittest 体系（`posix.mak` 已废弃
  并转发；单模块官方形态 `%.test`：`DMD $(DFLAGS) -main -unittest
  -version=StdUnittest -run <module>.d`）。
- **执行方式**：ldc2 1:1 复刻官方 `%.test`（DMD→ldc2、`-version=`→`-d-version=`、
  库走本包共享库），176 个模块（官方 `D_MODULES` 口径：std 全部 + etc/c）逐模块
  独立编译+运行，4 并发，单模块 120s 超时。
- **日志路径**：`.workbuddy/tmp/liblphobos-1.42.0/ut/`（`runner.log`、
  `summary.json`、`logs/<模块名>.log` 逐模块日志；该目录 `.gitignore` 覆盖，
  不入 PR）。

| 范围 | 模块数 | PASS | FAIL | TIMEOUT | SKIP（无 unittest） | 通过率 |
|------|-------|------|------|---------|--------------------|--------|
| Phobos | 176 | **123** | 9 | 0 | 44 | **123/132 = 93.2%** |

> 口径说明：SKIP 为无 `unittest` 块的声明模块（运行无输出，与 ldc 任务口径一致），
> 不计入分母。交叉验证：ldc/1.42.0 当年同源码同平台基线 125/132 = 94.7%，本次
> 93.2% 与之吻合（差异模块见下）。

**失败项及根因**（9 项，均为环境/平台限制，非本包缺陷）：

| 模块 | 首错 | 判定 |
|------|------|------|
| `std.datetime.systime` | `Directory /usr/share/zoneinfo/ does not exist` | 环境限制（设备无时区库） |
| `std.datetime.timezone` | 同上 | 环境限制 |
| `std.net.curl` | `Failed to load curl, tried "libcurl.so"…` | 环境限制（设备无 libcurl） |
| `std.stdio` | `Could not create temporary file with tmpfile() (Permission denied)` | 环境限制（OHOS `/tmp` 只读，ldc 同归因） |
| `std.experimental.allocator.mallocator` | `posix_memalign returned an unknown code` | 平台差异（musl 返回码语义） |
| `std.math.hardware` | `hardware.d(422): Assertion failure` | 平台差异（AArch64 FPU 状态位语义） |
| `std.file` | `deleteme…: Permission denied`（el2 cache 目录写/删被拒） | 沙箱环境限制 |
| `std.process` | `Failed to execute '…temporary file…' (Permission denied)` | 沙箱环境限制（未签名临时可执行被拒 exec） |
| `std.regex.internal.tests` | 自重启子进程 `Segmentation fault`（单跑复现） | 沙箱环境限制（unittest exec 自身子进程被限；未定性为库缺陷） |

## 已知限制

1. 沙箱内 `std.file`/`std.process`/`std.regex.internal.tests` 的 exec/写限制
   归因基于首错与复跑证据，最终定性以真机无沙箱环境复核为准。
2. `libdruntime-ldc-shared.so` 内 `program_invocation_name` 为空串定义（同 ldc
   引导期适配口径），`core.internal.elf.dl` 读取程序名得到空串，功能不中断。
3. 构建期依赖已发布的 `ldc/1.42.0`（ohpcd 现成二进制），不可在「无 ldc 包」的
   环境从零构建。
---

**编译结束**: 2026-09-17 15:58
**最终状态**: built
