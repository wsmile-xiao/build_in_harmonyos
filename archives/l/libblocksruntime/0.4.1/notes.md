# libblocksruntime 0.4.1 适配笔记

## 编译环境
- 构建系统: custom（上游为 autotools，见下）
- 编译日期: 2026-09-15
- 编译器: OHOS clang（Conan profile `ohos-aarch64`）
- 状态: built

## 版本与源码
- 上游 `mackyle/blocksruntime` **没有 0.4.1 tag**；`0.4.1` 是发行版发布身份：
  发行版源码包 `libblocksruntime_0.4.1.orig.tar.gz`
  （`configure.ac: AC_INIT([libBlocksRuntime], [0.4.1])`）。
- 该 tarball 的 `runtime.c` / `data.c` 与 mackyle master **不同**
  （`Block.h`/`Block_private.h` 相同），因此 0.4.1 是真实发布源码，不是简单
  取 master。
- 源码：`https://deb.debian.org/debian/pool/main/libb/libblocksruntime/libblocksruntime_0.4.1.orig.tar.gz`
  sha256 `7807e18d7d6cabd90f77c8b8a8ebd472516fa4ed6a02df82e0c33b1c5e112abc`（312180 字节）。

## 为什么不用上游 autotools 直接构建

在真机实测（E007 / E074）：

1. 发行包自带 2013 版 `config.guess`/`config.sub`，不识别 HarmonyOS：
   - `configure: error: cannot guess build type; you must specify one`
   - 且 `config.guess` 在 HMDFS 上写 `dummy.c` 探针报 `Permission denied`。
2. 按 E007 换成 GNU 最新 `config.guess`/`config.sub` + `patch-autotools-ohos.pl`
   后，`config.guess` 已能输出 `aarch64-unknown-linux-ohos`，但新版
   `config.sub` 仍拒绝 `linux-ohos` 组合
   （`Kernel 'linux' not known to work with OS 'ohos'`）。
3. `make -j2` 在 HMDFS 上失败：`jobserver mkfifo: ... Operation not permitted`。

上游构建物只有 `runtime.c` + `data.c` 两个翻译单元，直接编译确定性更高、
也更小。本项目其余“直接编译”先例同理。

## 编译步骤

```sh
# 生成上游 configure 会生成的 config.h（功能上仅版本串）
printf '#define PACKAGE_VERSION "0.4.1"\n' > <build>/config.h
# 编译（config2.h 已携带原子操作能力宏：HAVE_SYNC_BOOL_COMPARE_AND_SWAP_INT/LONG）
clang -c -O2 -std=c99 -fPIC -I <src> -I <build> -o runtime.o runtime.c
clang -c -O2 -std=c99 -fPIC -I <src> -I <build> -o data.o data.c
llvm-ar rcs libBlocksRuntime.a runtime.o data.o
```

`package()` 安装 `include/Block.h`、`include/Block_private.h`、
`lib/libBlocksRuntime.a`、`licenses/LICENSE.TXT`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `-fblocks` 可编译但链接失败 | OHOS clang/SDK 无 Blocks 运行库、无 `Block.h` | 打包独立 BlocksRuntime，消费者 `-fblocks` + `-lBlocksRuntime` |
| 2 | `configure` 报 `cannot guess build type` | 2013 `config.guess` 不认 HarmonyOS（E007） | 不走上游 autotools，直接编译 |
| 3 | `make -j2` 失败 | HMDFS jobserver FIFO（E074） | 不使用 make |
| 4 | `runtime.c` `#include "config.h"` | 上游 configure 生成物，tarball 不含 | build() 生成最小 config.h |
| 5 | 发行包无 LICENSE 文件 | 仅供头文件内嵌许可 | 复刻头文件许可文本为 `licenses/LICENSE.TXT` 并随配方导出 |
| 6 | 独立 clang 链接报 `posix_spawn failed` | harmonybrew 的 clang 23.x 无链接器驱动 | 用 SDK clang（profile `tools.build:compiler_executables.c`）才能看到真正的 `undefined symbol` |

## 运行库行为观察（0.4.1 实测）

这些是本运行库版本的真实行为，写进测试断言时需注意：

1. `_Block_copy` **不重标 isa**：堆拷贝仍是 `_NSConcreteStackBlock`，仅置
   `BLOCK_NEEDS_FREE | 1`（`runtime.c:202-212`），不设置 `_NSConcreteMallocBlock`。
   判断“是否堆块”应看 `BLOCK_NEEDS_FREE`，而不是 `isa`。
2. 无捕获的块是 **global block**（`BLOCK_IS_GLOBAL`），`Block_copy` 原样返回，
   **不会**置 `BLOCK_NEEDS_FREE`。
3. `_Block_dump()` 对现代 clang 编出的块会 `exit(1)`：clang 不再设置 legacy 的
   `BLOCK_HAS_DESCRIPTOR` 位，而 `_Block_dump` 要求该位（`runtime.c:462-465`）。
   不要在生产诊断路径里依赖它。
4. `__block`（byref）块的 `BLOCK_HAS_COPY_DISPOSE` 会置位，即编译器生成了调用
   `_Block_object_assign`/`_Block_object_dispose` 的助手函数。

## 源码修改

无补丁（`patches/` 为空）。

## 消费者验证（test_package）

三个消费者（均 `ctest` 实跑，32 项断言 + 上游 1 项）：

1. `test_upstream.c` — 上游 0.4.1 自带测试 verbatim（`test/main.c`）。
2. `test_blocks_c.c` — 独立 C 消费者：stack/malloc/global block 类别、
   `Block_copy`/`Block_release` 生命周期、`__block` byref 共享、块作参数/
   嵌套/数组/结构体捕获、`Block_copy(NULL)`、`_Block_dump`。
3. `test_blocks_cpp.cpp` — C++ 消费者：**不自行传 `-fblocks`**，验证运行库
   传播语言开关；覆盖 `std::string`/自定义拷贝构造对象捕获、`__block`、
   块参数/返回块/嵌套。

## 编译期/链接期 2×2 矩阵（真机实测，SDK clang 15）

| 配置 | `-fblocks` | 链接运行库 | 结果 |
|------|:---------:|:---------:|------|
| 编译检查 | ✅ | — | `rc=0`（只有编译过，不代表可用） |
| 无语言开关 | ❌ | 任意 | `error: blocks support disabled - compile with -fblocks or pick a deployment target that supports them` |
| 有开关、无运行库 | ✅ | ❌ | `ld.lld: error: undefined symbol: _NSConcreteStackBlock / _Block_copy` |
| 两者齐备 | ✅ | ✅ | 编译+链接+运行 `rc=0` |

诊断陷阱：独立发行的 `harmonybrew/bin/clang`（无链接器驱动）直接链接报
`posix_spawn failed: No such file or directory`，与缺库无关；真错误要用 profile 指向的
SDK clang 复现。

## 独立上游语料验证（mackyle BlocksRuntime/tests，51 文件）

用 `-fblocks -include testprefix.h` 对**已安装的** `libBlocksRuntime.a` 编译运行
（无 `main` 的用例改 `-c`）：

| 结果 | 数量 | 说明 |
|------|:---:|------|
| PASS（运行/编译检查） | 35 | byref 家族、递归块、结构体/可变参数、C++ 等 |
| 负向编译用例复现 | 7 | `constassign`/`k-and-r`/`orbars`/`rettypepromotion`/`shorthandexpression`/`sizeof`/`varargs-bad-assign` |
| 跳过（记明原因） | 6 | 4× 需 `libdispatch`；2× 需 ObjC-GC |
| 上游 legacy 预期偏离 | 3 | `hasdescriptor.c`（尺寸 36 vs 40）、`copy-block-literal-rdar6439600.c`（上游 `CONFIG open`）、`voidarg.c` |
| **OHOS 回归失败** | **0** | — |

## 验证结果

```bash
conan create archives/l/libblocksruntime/0.4.1 \
  -pr:h=$HOME/.conan2/profiles/ohos-aarch64 -pr:b=$HOME/.conan2/profiles/ohos-aarch64
# -> ctest: 3/3 consumers passed（含上游 test_upstream）
# 另：2×2 矩阵 + 独立上游语料 51 文件（0 回归）
```

## 注意事项

- 消费者若自行管理编译选项，务必同时加 `-fblocks` **并** 链接
  `-lBlocksRuntime`；只做其中一项都会失败（编译期或链接期）。
- `data.c` 以 `__attribute__((weak))` 导出 `_NSConcrete*Block`，
  这是编译器 lowering 所依赖的符号。
