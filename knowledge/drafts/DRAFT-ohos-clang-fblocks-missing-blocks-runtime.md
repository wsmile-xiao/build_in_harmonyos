# DRAFT-ohos-clang-fblocks-missing-blocks-runtime — OHOS clang 的 Blocks：有 `-fblocks` 不等于有运行库

## 错误特征

含块代码（`^{ ... }`）在 OHOS 上**编译成功、链接失败**：

```
ld.lld: error: undefined symbol: _NSConcreteStackBlock
>>> referenced by blocks.c
>>>               blocks.o:(main)

ld.lld: error: undefined symbol: _Block_copy
>>> referenced by blocks.c
>>>               blocks.o:(main)

ld.lld: error: undefined symbol: _Block_object_dispose
>>>               blocks.o:(__destroy_helper_block_8_32r)
```

未定义符号是一个**家族**（出现哪些取决于用到的块特性）：`_Block_copy` / `_Block_release`
（拷贝释放）、`_Block_object_assign` / `_Block_object_dispose`（`__block`、对象字段的
copy/dispose 助手）、`_NSConcreteStackBlock` / `_NSConcreteMallocBlock` /
`_NSConcreteGlobalBlock`（块类对象 / `isa`）。

## 触发条件

- 平台：OHOS（HarmonyOS PC，clang/SDK，musl）；任何“clang 有 `-fblocks`、但没装 BlocksRuntime”的平台同理。
- 阶段：**linking**（编译不报错，容易误判“语言特性可用”）。
- 代码模式：任意块用法——字面量、`Block_copy`/`Block_release`、捕获变量、`__block`、
  块作参数/返回值/存数组、用它做回调 API。
- 依赖：直接或间接依赖任何用 Blocks 的第三方库。

## 根因分析：两个独立交付物，缺一不可

Clang 的 Blocks 被拆成**编译期语言开关**与**链接期运行库**两半：

1. `-fblocks` 让编译器 lowering `^{...}`，并生成对运行库的调用；
2. 运行库是 LLVM compiler-rt 的 **BlocksRuntime**（`_Block_copy` 等 + `_NSConcrete*Block`），
   Linux 发行版以 `libblocksruntime` 提供 —— **既不是 libc 的一部分，也不是编译器自带**。

OHOS 的 clang 有第 1 半、没有第 2 半：**SDK 不带 BlocksRuntime，也不安装 `<Block.h>`**。
所以错误只在链接期出现。两端独立且都必需，可用下表判定（真机 OHOS aarch64，SDK clang 15 实测）：

| 配置 | `-fblocks` | 链接运行库 | 结果 |
|------|:---------:|:---------:|------|
| (1) 编译检查 | ✅ | — | `rc=0`（**只有编译通过，什么都证明不了**）|
| (2) 无语言开关 | ❌ | — | 编译期失败：`error: blocks support disabled - compile with -fblocks or pick a deployment target that supports them` |
| (3) 有开关、无运行库 | ✅ | ❌ | 链接期失败：`ld.lld: error: undefined symbol: _NSConcreteStackBlock / _Block_copy` |
| (4) 两者齐备 | ✅ | ✅ | 编译+链接+运行 `rc=0` |
| (5) 无开关、链接库 | ❌ | ✅ | 同 (2)——**链接库救不了缺语言开关** |
| (6) 无开关、无库 | ❌ | ❌ | 同 (2) |

结论：**“能编译” ≠ “平台支持 Blocks”**；只补一端（无论哪端）都不通。

### 诊断陷阱（实测）

用没有链接器驱动的独立 clang（`harmonybrew/bin/clang` 23.x）直接链接会报：

```
clang: error: unable to execute command: posix_spawn failed: No such file or directory
```

这与“缺运行库”无关，纯粹是该 clang 找不到链接器。真正的缺库错误必须用 SDK clang
（Conan profile 的 `tools.build:compiler_executables.c`，如
`.../ohos-sdk@26.0.0.18/native/llvm/bin/clang`）才能看到上面 `ld.lld: undefined symbol`。

## 使用说明 / 适用范围 / 输入输出 / 示例

### 使用说明（三步）

1. **定位缺哪一端**：按下面 2×2——编译期报 `blocks support disabled` → 缺 `-fblocks`；
   编译过但链接报 `undefined symbol: _Block_*` → 缺运行库；两者齐备即通过。
2. **补运行库并让包传播语言开关**：引用 `libblocksruntime/0.4.1`（本仓
   `archives/l/libblocksruntime/0.4.1/`），消费者只写
   `target_link_libraries(app PRIVATE BlocksRuntime::BlocksRuntime)`（`-fblocks` 随包带入）。
3. **按示例验证**：用下面「示例」的 4 条命令确认链接+运行通过；若项目自有上游测试，
   再按 R51 清点并运行。

### 适用范围

- **适用**：任何在 OHOS（clang/SDK，musl）上使用 clang Blocks（`^{...}`/`-fblocks`）的
  C/C++ 项目或库，含间接依赖方；其它“有 `-fblocks`、无 BlocksRuntime”的平台同理。
- **不适用**：编译器未实现 `-fblocks` 的情形（本条目解决的是“有语言特性、缺运行库”）；
  以及 Objective-C ARC/GC 的完整 ObjC 运行时（本条目只覆盖 C/C++ 块所需的 BlocksRuntime 子集）。

### 输入 / 输出

| | 内容 |
|---|---|
| **输入** | ① 一个含块代码的 C/C++ 项目（或报错日志：`undefined symbol: _Block_copy/_Block_object_assign/_NSConcreteStackBlock` 或 `blocks support disabled`）；② OHOS clang/SDK + Conan profile（`os=OHOS, arch=armv8, compiler=clang`）|
| **输出** | ① 缺口的判定结论（编译期门 / 链接期门 / 两者都缺）；② 可复用产物：`libblocksruntime` 运行库包（`lib/libBlocksRuntime.a` + `include/Block.h`、`Block_private.h`，并经 `cpp_info.cflags/cxxflags` 传播 `-fblocks`）；③ 验证结果：链接+运行通过、独立上游语料 0 回归、消费者 N/N 通过 |

### 示例

最小可复现（真机 OHOS aarch64 / SDK clang 15 实测）：

```c
/* blocks.c */
#include <Block.h>
typedef int (^IntBlock)(void);
int main(void){ __block int i=0; IntBlock b = Block_copy(^{ return ++i; });
                int r=b(); Block_release(b); return r==1?0:1; }
```

```sh
CC=<SDK clang>                                  # profile 的 tools.build:compiler_executables.c
$CC -std=c99 -fblocks -c blocks.c -o blocks.o && echo "compile OK"      # 编译期门通过
nm blocks.o | grep ' U _Block'                                          # 符号悬空：U _Block_copy ...
$CC -fblocks blocks.c -o b && ./b                                       # 期望失败：undefined symbol
$CC -fblocks blocks.c -lBlocksRuntime -o b && ./b; echo rc=$?           # 期望 rc=0
```

CMake 消费者（语言开关由包带入）：

```cmake
find_package(BlocksRuntime REQUIRED)
add_executable(app blocks.c)
target_link_libraries(app PRIVATE BlocksRuntime::BlocksRuntime)   # 自带 -fblocks
```

## 解决方案

### 推荐方案：独立运行库包 + 传播 `-fblocks`

1. 制品仓提供独立运行库包：把 compiler-rt BlocksRuntime（发行版发布源码
   `libblocksruntime_0.4.1.orig.tar.gz` 的 `runtime.c` + `data.c`）编成
   `lib/libBlocksRuntime.a`，安装 `include/Block.h`、`include/Block_private.h`。
   本仓实例：`archives/l/libblocksruntime/0.4.1/`。
2. **由运行库包传播语言开关**（本模式的关键）：

   ```python
   # conanfile.py
   self.cpp_info.libs = ["BlocksRuntime"]
   self.cpp_info.cflags = ["-fblocks"]
   self.cpp_info.cxxflags = ["-fblocks"]
   self.cpp_info.set_property("cmake_file_name", "BlocksRuntime")
   self.cpp_info.set_property("cmake_target_name", "BlocksRuntime::BlocksRuntime")
   ```

   消费者于是只需：

   ```cmake
   find_package(BlocksRuntime REQUIRED)
   target_link_libraries(app PRIVATE BlocksRuntime::BlocksRuntime)  # 自带 -fblocks
   ```

   这把“两个独立交付物”在包管理层重新绑成一个动作，从机制上消除上表的 (3)/(5) 两种半配置。
   本仓 C++ 消费者**故意不自行传 `-fblocks`**，即用来证明传播生效。

### 禁止做法（实测依据）

- ❌ **只加 `-fblocks` 不链库**：编译期过，链接期必失败（上表 (3)，实测 `ld.lld undefined symbol`）。
- ❌ **只链库不加 `-fblocks`**：编译期即 `error: blocks support disabled ...`（上表 (5)/(6)，
  是否链接运行库无关）。
- ❌ **把 `posix_spawn failed` 当根因**：那是独立 clang 没有链接器驱动，不是缺库；用 SDK clang 复现真错误。
- ❌ **只提供 `Block.h` 头**：头里只有声明，符号实体在运行库里；会表现成“include 了 `Block.h` 仍 undefined”。

### 验证

```sh
CC=<SDK clang>; LIB=<prefix>/lib/libBlocksRuntime.a
$CC -std=c99 -fblocks -c b.c -o b.o && nm b.o | grep ' U _Block'   # 编译期过但符号悬空
$CC -std=c99 -fblocks b.c -o b 2>&1 | grep 'undefined symbol'      # 无库：失败
$CC -std=c99 -fblocks b.c "$LIB" -o b && ./b                        # 有库：rc=0
conan create archives/l/libblocksruntime/0.4.1 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
```

## 通用性证据（独立上游语料，非自写消费者）

用 mackyle/blocksruntime 仓库自带测试集（`BlocksRuntime/tests/`，**51 个文件，独立于本包**）
对**已安装的** `libBlocksRuntime.a` 编译运行（`-fblocks -include testprefix.h`，无 `main` 的改 `-c`）：

| 结果 | 数量 | 说明 |
|------|:---:|------|
| PASS（编译+运行） | 32 | 覆盖 byref 家族、结构体捕获、递归块、`Block_copy`/release、嵌套、K&R、可变参数、C++ 等 |
| PASS（编译检查） | 3 | `byrefcopycopy.c` / `byrefsanity.c` / `macro.c`（无 main 的上游编译用例）|
| 负向编译用例复现（XFAIL-OK） | 7 | `constassign`/`k-and-r`/`orbars`/`rettypepromotion`/`shorthandexpression`/`sizeof`/`varargs-bad-assign` 均如上游标注般编译失败 |
| 跳过（记明技术原因） | 6 | 4 个需 `libdispatch`（`dispatch_async`、`dispatch_call_Block_with_release`、`rdar6405500`、`rdar6414583`）；2 个需 ObjC-GC（`objectRRGC`、`josh.C`）|
| **OHOS 特有回归失败** | **0** | — |

另有 3 个用例是**上游 legacy 预期**偏离（非本适配引入），见同目录第二稿
`DRAFT-blocksruntime-runtime-behavior-and-lifecycle-verification`。

## 同类问题族与判定决策（可复用）

本条目解决的问题属于一个**可判定、可复用**的类别：

> **编译器已实现的语言/代码生成特性（由编译期开关触发），其所需的独立运行库未随目标平台提供。**

**三步判定（同族问题通用）：**

1. **特性只由编译期开关控制吗**：`<CC> <flag> -c <tu>` 是否成功；
2. **所需运行库符号是否悬空**：`nm <obj> | grep ' U '`（注意：**只加开关、但翻译单元里没有对应代码时不会引用运行库符号**——本任务实测 `-fblocks` 编译一个无块代码的 `s.c` 能正常链接，必须用**含该特性的代码**判定）；
3. **SDK 是否提供该运行库**：`<CC> -print-resource-dir` + `ls <sdk>/native/llvm/lib`，或直接链接探测。

**OHOS SDK 实测（2026-09-15，ohos-sdk@26.0.0.18，SDK clang 15）：**

| 编译器特性（编译期开关） | 所需运行库 | OHOS 是否提供 | 实测判据 |
|---|---|:---:|---|
| `-fopenmp` | `libomp.so` / `libgomp.so` / `libiomp5.so` | ✅ | `llvm/lib` 下有该库；含 `#pragma omp` 的程序链接+运行 `rc=0` |
| `-fsanitize=address` | compiler-rt ASan | ✅ | 链接+运行通过（`val=3`） |
| `-fsanitize=thread` | compiler-rt TSan | ✅ | 链接+运行通过 |
| `-fprofile-instr-generate` | compiler-rt profile | ✅ | 链接+运行通过 |
| **`-fblocks`（含块代码）** | **BlocksRuntime** | **❌** | 无 `libBlocksRuntime`、无 `Block.h`；含块代码链接期 `undefined symbol: _Block_*` |

→ 通用处置：先按三步判定"缺哪一端"；**若缺运行库，按本条目"打包运行库 + 传播语言开关"处置**。
不要把"编译通过"当成"平台支持"，也不要默认"编译器特性 = 运行库自带"（同一 SDK 里 openmp/sanitizer 自带、Blocks 却缺，正说明必须逐项检查）。

## 复用方式（后续参赛者接入清单）

下游库/工具接入，任选其一：

1. **Conan 依赖（推荐）**：`self.requires("libblocksruntime/0.4.1")`；消费者侧
   ```cmake
   find_package(BlocksRuntime REQUIRED)
   target_link_libraries(<target> PRIVATE BlocksRuntime::BlocksRuntime)  # -fblocks 随包带入
   ```
2. **非 Conan 项目**：`-fblocks` 编译 + `-I<prefix>/include -L<prefix>/lib -lBlocksRuntime`
   （`Block.h`/`Block_private.h` 由本包提供）。
3. **不能引外部包**：按 fallback vendor `runtime.c`+`data.c`（见本包 `notes.md`）。

接入自检：按「示例」4 条命令验证；或仿本包 `test_package` 的 3 个消费者
（上游测试 + 独立 C + C++）与 `ctest` 全绿。

## 查重反证（与既有正式条目）

- **检索反证（新增性）**：
  ```sh
  ls -1 knowledge/graph/E[0-9][0-9][0-9].kv | wc -l                        # 540
  grep -rli "blocksruntime\|fblocks\|Block_copy\|_Block_object_assign" \
       knowledge/graph knowledge/doc | wc -l                             # 0
  ```
  540 条正式条目中 **0 命中** Blocks / `-fblocks` / BlocksRuntime。
- **E003（`-lpthread`）/ E013（`-ldl`）**：库已在系统里，只差链接参数；本条目运行库在 OHOS 上
  **不存在**，须先适配入库。反证：`-lpthread` 加参数即 rc=0；本条目加 `-fblocks` 后仍失败，
  必须额外提供包。
- **E019（运行期找不到 `.so`）**：产物已链接成功、是部署/RPATH 问题；本条是**链接期缺符号**。
- **E213（本地实现缺失 API）**：补单个函数/接口；本条补的是**一套运行时 + 语言开关传播**，
  且两个交付物必须同时到位。

## 证据

- 适配 PR：`feat/libblocksruntime-0.4.1`（任务 contrib-13066，issue #3029）。
- 配方：`archives/l/libblocksruntime/0.4.1/`（conanfile + conandata + test_package +
  README + notes + reports）；运行库包 `libblocksruntime/0.4.1@ohpcd/stable`。
- 本包消费者：`ctest` 3/3（上游 `test/main.c` verbatim + 独立 C 21 断言 + C++ 10 断言）。
- 独立上游语料：见上表（51 文件，0 回归）。
- 真机日志：2×2 矩阵与 `ld.lld` 输出见「验证」段。

## 元信息

- authors: `frj__`（contributor_id: `frj__`）
- source_event: libblocksruntime 0.4.1 OHOS aarch64 适配（2026-09-15）
- draft: true —— 待主编审核后 promote 为正式 E 条目
