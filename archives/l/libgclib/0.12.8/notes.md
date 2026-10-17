# libgclib 0.12.8 适配笔记

## 编译环境
- 构建系统: **manual**（上游无 CMake / autotools / meson，仓库根只有一份手写
  Makefile；本包在 `build()` 里自己编排编译与链接命令）
- 编译日期: 2026-09-20
- 编译器: clang / clang++（OHOS aarch64 工具链，`ci/conan/profiles/ohos-aarch64`）
- 状态: built（`conan create` 通过 ohos-aarch64 profile）

## 上游身份
- 仓库: https://github.com/gpertea/gclib （默认分支 master）
- release tag: **`v0.12.8`**（**带 `v` 前缀**）
- tarball SHA-256: `a8dea4d273d6802f77f26a5394b1d66dfc1aba46a725c61e4c7399b756fb75e3`
- 解出目录 `gclib-0.12.8`，配方 `strip_root=True` 拉平
- 许可: MIT（`LICENSE.txt` 单独 copy 到 `licenses/`）
- gclib 是 GPertea 的通用 C++ 工具库（GStr / GArgs / GList / GVec / GHash /
  GHashMap / FASTA 解析 / 线程封装 / 内存采样 / 碱基与密码子表），是
  **GFFread、StringTie** 等基因组工具的共同底座
- **master 与 v0.12.8 的文件集逐条相同**（57 个条目，已用 GitHub contents API
  复核），因此对默认分支做朴素扫描与对钉版 tag 做扫描结论一致

## 编译步骤

上游仓库根 `Makefile` 只有：

```make
OBJS := GBase.o GStr.o GArgs.o GResUsage.o
all: htest
BASEFLAGS := -std=c++11 -Wall -Wextra ${INCDIRS} $(MARCH) -D_REENTRANT -fno-exceptions -fno-rtti
LIBS := -lz
```

没有库目标（无 `.so`/`.a` 规则）、没有 `install:` 规则。GFFread / StringTie
的既有用法是把上面这 4 个 `.o`（乃至全部 16 个）直接链进自己的可执行文件。
**"库的边界"必须由本配方自己定义**，配方取的是"能自洽编译的全部库翻译单元"。

1. 逐 TU 编译（16 个）：`clang++ <source_flags> -fPIC -I<src> -c <tu>.cpp -o <tu>.o`
   - `source_flags = -std=c++11 -D_REENTRANT -fno-exceptions -fno-rtti -O2`
     （前四个照抄上游 `BASEFLAGS`；`-O2` 取 Release 语义，与 profile 的
     `build_type=Release` 一致。上游的 `-Wall -Wextra` 是诊断项，不进产物）
   - `fPIC` 由选项控制，shared 与 static 都按 `-fPIC` 编
2. 链接：
   - shared: `clang++ -shared -pthread -Wl,-soname,libgclib.so -o libgclib.so *.o`
   - static: `llvm-ar rcs libgclib.a *.o`
3. `package()`：
   - copy `LICENSE.txt`
   - 从 build 树取 `libgclib.so` / `libgclib.a`（缺失即 `ConanException`）
   - copy 24 个发运头；**逐条数校验**（staged != 24 即抛错），
     防止"静默少装"被当成通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游没有库产物，无从"照抄" | 仓库根 Makefile 只有 `all: htest`，`OBJS` 是给下游直接链 `.o` 用的；无 `.so`/`.a` 目标、无 `install:` | 配方自己定义边界：编译全部 16 个库 TU，分 shared/static 两种链接方式产出 `libgclib.so` / `libgclib.a`，`package()` 自管头文件与库文件 |
| 2 | release tarball 编不全（22 个 .cpp 里有 3 个必失败） | `GBam.cpp` 需要 htslib 的 `kstring.h`/`sam.h`/`bam.h`；`gdimg.cpp` 需要 libgd 的 `gd.h`；`gff.cpp` 需要 boost 的 `boost/crc.hpp`。三者都不随包发布，也没有任何 `pkg-config`/`CMake` 探测可把这层依赖变成显式选项 | 只编译剩下的 16 个库 TU；被排除的 6 个头（`GBam.h`/`gdimg.h`/`gff.h`/`GBitVec.h`/`GIntHash.hh`/`GIntervalTree.hh`）连同理由如实列在下方"头文件取舍"。另 3 个带 `main()` 的演示程序（`htest.cpp`/`mdtest.cpp`/`gtest.cpp`）天然不入库 |
| 3 | 头文件发运集合怎么定才不留"发运了却编不过"的头 | 上游没有 install 规则，也就没有官方头文件清单 | 发运集合 = **已编译 TU 的 quoted-include 闭包（24 个）**。闭包算法的性质保证：每个被发运的头都在 `build()` 里被某个被编译的 TU 真实包含过，因此不存在"发运了却编不过"的头 |
| 4 | `#include "config.h"` / `<config.h>` 在源码树里不存在 | `GBase.h` 的 `"config.h"` 受 `HAVE_CONFIG_H` 守卫，`GArgs.h` 的 `<config.h>` 同一守卫；上游 Makefile 不定义该宏 | 不定义 `HAVE_CONFIG_H`，守卫直接挡住，两条 include 从不展开 → 不构成依赖。同名情况还有 `proc_mem.cpp` 的 `"windows.h"`/`"psapi.h"`（受 `_WIN32` 守卫） |
| 5 | `-lz` 是不是必需依赖 | 上游 `LIBS := -lz` 是给 `gff.cpp`（boost 路径）与 `GBam.cpp`（htslib 路径）用的，二者本包都不编译；`GCdbYank.h` 的 `<zlib.h>` 与整个 `GCdbZFasta` 类都在 `#ifdef ENABLE_COMPRESSION` 里，而上游 Makefile 未定义该宏 | 不引入 zlib：本包**零第三方依赖**。（若将来要打开 `ENABLE_COMPRESSION`，需要同时补 `-DENABLE_COMPRESSION` 与 `requires("zlib/...")`） |
| 6 | libgclib 按 `-std=c++11` 编，而 OHOS profile 的 `compiler.cppstd` 是 17 | 上游 `BASEFLAGS` 钉 `-std=c++11`；消费者（OHOS profile）用 c++17 | 链接侧实测可互链：gclib 全库零 `throw`、零 `dynamic_cast`/`typeid`，`-fno-exceptions -fno-rtti` 只影响异常表与 RTTI 元数据的生成。**但头文件侧不行**：`GList.hh` 声明/定义的异常规格不一致，`-std=c++17` 下是硬错误，见下文"必须打补丁"一节 → 打 `patches/0001-glist-move-ctor-noexcept-declaration.patch`。test_package 用同一份源码在 `-std=c++11` 与 `-std=c++17` 下**各编一次各跑一次**，两次都必须链接成功、83 条断言全绿 —— 就是这一趟 c++17 把上述问题炸出来的 |

## 源码修改

**一个补丁**（`patches_applied: ["patches/0001-glist-move-ctor-noexcept-declaration.patch"]`）：

| 文件 | 改动 | 理由 |
|---|---|---|
| `GList.hh:101` | `GList(GList<OBJ>&& list);` → `GList(GList<OBJ>&& list) noexcept;` | 声明缺 `noexcept`，而 `:375` 的定义有；C++11 下 clang 放过（尤其配 `-fno-exceptions`），C++17 下 `noexcept` 已是函数类型的一部分、是硬错误，而 OHOS 消费者默认 c++17。只补齐声明一侧，保留作者"移动构造不抛"的显式意图 |

上游 16 个库 TU（`.cpp`）一行未动；24 个发运头里只有 `GList.hh` 这一行被改，
且全仓库 `noexcept` 只出现在这一处。其余 5 个问题都在"配方侧选边界 / 选开关"
层面解决，不需要动上游源码；另一个"改文件"的动作是 `package()` 里把库与头
拷进 package，属于打包而非修补。

## 依赖版本
- **无第三方依赖**（standalone）。`conanfile.py` 的 `requirements()` 为空。
- 无 `tool_requires`：无需 CMake / autotools，只用 profile 注入的
  `clang++` 与 `llvm-ar`。
- 上游 tarball 自带的 `xxhash.h` / `wyhash.h` / `khashl.hh` 是 vendored 头
  （single-header 库），随包发运，同样不构成 Conan 依赖。

## 头文件取舍（24 发运 / 6 排除）

发运（= 16 个已编译 TU 的 quoted-include 闭包，每个都在 build() 里真实编译过）：

```
GBase.h GStr.h GArgs.h GResUsage.h GThreads.h gcdb.h GCdbYank.h gsocket.h
gstopwatch.h proc_mem.h codons.h gdna.h GAlnExtend.h GFastaIndex.h
GFaSeqGet.h GapAssem.h GFastaFile.h
GList.hh GVec.hh GHash.hh GHashMap.hh khashl.hh wyhash.h xxhash.h
```

排除（连同理由）：

| 头 | 理由 |
|----|------|
| `GBam.h` | 其 TU `GBam.cpp` 需要 htslib 的 `kstring.h`/`sam.h`/`bam.h`，不随包发布 |
| `gdimg.h` | 其 TU `gdimg.cpp` 需要 libgd 的 `gd.h`，不随包发布 |
| `gff.h` | 其 TU `gff.cpp` 需要 boost 的 `boost/crc.hpp`，不随包发布 |
| `GBitVec.h` | 文件名是 `.h`（不是 `.hh`），且不被任何已编译 TU 包含 |
| `GIntHash.hh` | 不被任何已编译 TU 包含 |
| `GIntervalTree.hh` | 不被任何已编译 TU 包含 |

### 这 24 个头**不能**同处一个 TU：两个同名的 `class GHash`

消费者侧「24 个头都能被包含」的契约必须拆成两个 TU 才成立，原因是上游留了
一对同名不同签名的类模板：

| 头 | 定义 | 谁包含它 |
|----|------|---------|
| `GHash.hh` | `template <class OBJ> class GHash`（char* 键的旧式哈希表） | `GapAssem.h:6` |
| `GHashMap.hh` | `template <class V, class Hash=…, class Eq=…, typename khInt_t=uint64_t> class GHash` | `GFastaIndex.h` ← `GFaSeqGet.h` |

两者 headerguard 不同（`GHash_HH` / 各自的守卫），名字却相同，任何 TU 同时
包含就是硬错误：

```
GHash.hh:21:1: error: too few template parameters in template redeclaration
template <class OBJ> class GHash {
GHashMap.hh:389:1: note: previous template declaration is here
```

所以 test_package 拆成两个 TU：`test_libgclib.cpp` 装 GHashMap 簇的 22 个头，
`test_hdr_cluster_b.cpp` 装 `GapAssem.h` / `GHash.hh`，两者链接进同一个可执行
文件。上游自己的 `gff.h`/`htest.cpp` 只碰 GHashMap 簇，从不把两者放一起 ——
这是上游的一个隐含约束，不是本包引入的。

### `GList.hh` 的移动构造声明/定义异常规格不一致 —— **必须打补丁**

`GList.hh` 把移动构造**声明**成无 `noexcept`、**定义**成 `noexcept`：

```
GList.hh:101:5: note: previous declaration is here
    GList(GList<OBJ>&& list); //move constructor
GList.hh:375:34: error: exception specification in declaration does not match previous declaration
template <class OBJ> GList<OBJ>::GList(GList<OBJ>&& other) noexcept:
```

一开始本包在 `cpp_info.cxxflags` 里发布 `-fno-exceptions` 来压掉这条诊断 ——
**这只在 C++11 下成立**：clang 在 `-std=c++11` 且异常关闭时跳过声明/定义的
异常规格等价性检查。OHOS 消费者默认 `-std=c++17`，而 C++17 起 `noexcept`
已经是**函数类型的一部分**，该诊断不再受 `-fno-exceptions` 影响，照样报错。
实测（CI build #53438）：同一份 test_package，`-std=c++11` 那趟 83 条断言全绿，
`-std=c++17` 那趟第一行就死在 `GList.hh:375`。

所以正确处置是**打补丁修头文件**，而不是靠编译开关绕：

`patches/0001-glist-move-ctor-noexcept-declaration.patch` 只改声明一侧
（`:101` 补 `noexcept`），与定义保持一致。选择改声明而不是删定义的
`noexcept`，是为了保留作者的显式意图：移动构造保持 non-throwing，
`std::vector`（`GPVec` 的基类）重分配时仍会走移动而不是拷贝。

全 24 个发运头里 `noexcept` 只出现在这一处，所以补丁是单点、可控的。

### 那两个开关仍然要发布，但理由不是"绕开诊断"

`-fno-exceptions` / `-fno-rtti` 仍经 `cpp_info.cxxflags` 发布：

```python
self.cpp_info.cxxflags = ["-fno-exceptions", "-fno-rtti"]
```

理由换成了 ODR：gclib 是模板密集库，`GList<OBJ>`/`GVec<OBJ>`/`GHash<...>`
这些模板**同时**在库的 16 个 TU 里和消费者的 TU 里实例化（本包的 24 个头
全部发运，消费者必然会包含它们）。两侧的 `-fno-exceptions`/`-fno-rtti`
不一致，等于同一实体在不同 TU 里有两份语义不同的定义。这本来就是上游
`BASEFLAGS` 给下游定的 ABI 假设。

test_package 从 `dependencies["libgclib"].cpp_info.cxxflags` 取用（而不是自己
写死），顺带验证依赖方真的发布了这两个开关。

## 验证结果

本包在 OHOS aarch64 (`ci/conan/profiles/ohos-aarch64`) 下 `conan create` 通过，
`test_package` 全部执行：

```
libgclib/0.12.8 consumer contract test (__cplusplus=201103)
... 6 组 83 条 ...
checks=83 failures=0
libgclib/0.12.8 consumer contract OK

libgclib/0.12.8 consumer contract test (__cplusplus=201703)
... 6 组 83 条 ...
checks=83 failures=0
libgclib/0.12.8 consumer contract OK

=== OHOS specific #1: platform ABI of .../lib/libgclib.so ===
... 14 条 ...
=== OHOS specific #2: runtime contract ===
... 7 条 ...
checks=21 failures=0
libgclib/0.12.8 OHOS-specific checks OK
```

合计 **104 条断言**（83 条因 c++11/c++17 各跑一遍共执行 166 次）。

## 鸿蒙特有测试（rule12）

`test_package/test_ohos_gclib.cpp`，21 条断言 / 2 个场景，**不链接 libgclib**：
所有入口都经 `dlopen` + `dlsym` 取得，因此"符号被导出""加载器能解析"
"静态初始化已执行"三件事是真的被测到，而不是被链接期悄悄满足。

1. **平台 ABI 契约（14 条）**：直接解析 ELF 头与动态段 ——
   `ELFCLASS64` / `EM_AARCH64` / `PT_DYNAMIC` 存在；`DT_NEEDED` 链的是 musl
   `libc.so` 而非 glibc `libc.so.6`，链 `libc++_shared.so` 且无
   `libstdc++.so.6`；动态串表里能找到含 `ntComplement` / `translateCodon`
   的导出名；`dlopen(RTLD_NOW|RTLD_LOCAL)` 成功且 `dlsym` 能解析三个入口。
2. **运行时契约（7 条）**：`/proc/self/stat` 可读且 `get_mem_usage()` 返回非零
   vm/rss（证明 OHOS 落进 `proc_mem.cpp` 的 `#else //assume Linux` 分支、
   musl 的 `sysconf(_SC_PAGE_SIZE)` 可用）；`ntComplement('A')=='T'`、
   `ntComplement('a')=='t'`、`translateCodon("ATG")=='M'`、
   `translateCodon("TAA")=='.'` 全部在**从未显式调用** `gDnaInit()` /
   `codonTableInit()` 的前提下成立 —— 证明 `gdna.cpp` 的
   `static bool gdna_Ready=gDnaInit();` 与 `codons.cpp` 的
   `static bool isCodonTableReady=codonTableInit();` 这两处命名空间级静态初始化
   确实随 dlopen 的映射阶段（`.init_array`）执行了。
3. **只读根文件系统（由 `test_libgclib.cpp` 承担）**：临时目录按
   `$TMPDIR` → `$HOME` → `"."` 解析并断言可写，不写死 `/tmp` 或 `/var/tmp`；
   FASTA 写-读整条链路在该目录下完成。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | 自包含 manual 配方（16 TU 逐条编译 + shared/static 两种链接 + 闭包头文件打包 + 逐条数校验） |
| conandata.yml | 官方 URL + SHA-256 |
| test_package/test_libgclib.cpp | 消费者契约，6 组 83 条（`-std=c++11` 与 `-std=c++17` 各跑一遍） |
| test_package/test_ohos_gclib.cpp | 鸿蒙特有，2 场景 21 条（dlopen + dlsym，不链接 libgclib） |
| test_package/conanfile.py | 三次编译三次运行（c++11 / c++17 消费者 + ohos dlopen 测试） |
| test_package/MANIFEST.yml | 上游测试声明（0 条）+ test_package 测试与 assertion_count |
| manifest.yaml / notes.md | 版本元数据与适配笔记 |
| knowledge/drafts/DRAFT-libgclib-0.12.8-*.{md,kv} | 知识库扩展草稿 |

## 注意事项

- **rule4 口径**：上游**没有任何测试**。仓库没有 `test/` 目录、没有 CI 配置、
  没有发行版测试脚本；对默认分支 master 扫描
  `^TEST(` / `^TEST_F(` / `BOOST_AUTO_TEST_CASE` / `ctest` / `meson test` /
  `make check` 的命中数**均为 0**。朴素扫描 `assert(` 会得到 **8 处命中**，
  但逐条核验后全部不是可执行用例：
  - `gff.cpp` 3 处是被注释掉的 `//assert(...)`，且 `gff.cpp` 因缺
    `boost/crc.hpp` 根本不参与编译；
  - `xxhash.h` 1 处是 `#define XXH_ASSERT(c) assert(c)` 宏定义；
  - `GHashMap.hh` 4 处是编译期 `static_assert`。
  故上游测试数如实为 **0**，全部测试覆盖由 `test_package/` 提供。
- **`GList` 与 `GVec` 的 `Add` 语义不同**（消费者最易踩的坑，已写进
  test_package 场景 E）：`GList<OBJ>::Add(OBJ*)` 的非有序实现是
  `this->fList[result]=item;` —— **原样存指针、不拷贝**；而默认构造
  `GList(GCompareProc* =nullptr)` 会把 `fFreeProc` 设成 `DefaultFreeProc`，
  于是 `Clear()`/析构会对每个元素 `delete`。把栈对象地址 `Add` 进去会造成
  堆破坏，必须传 `new` 出来的对象。对照 `GVec<OBJ>::Add(OBJ*)` 是
  `fArray[fCount] = *item;` —— **真拷贝（值语义）**，可以放心传左值。
- **`translateCodon` 的终止密码子返回 `'.'`**（`codonData` 里 `'T','A','A','.'`），
  不是 `'+'` 也不是 `'*'`；未映射的密码子返回 `'X'`。`translateDNA` 返回的串
  由 `GMALLOC` 分配，消费者用 `free()` 释放（`GMALLOC` 即 `malloc`）。
- **库在加载期就完成碱基/密码子表初始化**：`gdna.cpp` 的
  `static bool gdna_Ready=gDnaInit();`（256 项互补表）与 `codons.cpp` 的
  `static bool isCodonTableReady=codonTableInit();`（32K 密码子表）都是
  命名空间级静态初始化，靠 `.init_array` 在库被映射时建好 ——
  **消费者从不显式调用** `gDnaInit()` / `codonTableInit()`。
- **`proc_mem.cpp` 在 OHOS 上走 `#else //assume Linux`**：平台分支是
  `__APPLE__` / (`_WIN32` \|\| `_WIN64`) / else，OHOS 落进 else，读
  `/proc/self/stat` 并用 musl 的 `sysconf(_SC_PAGE_SIZE)` 换算，因此
  **`/proc` 必须已挂载**。
- **A 组断言的 LP64 前提**：gclib 全程用 `off_t` + `fseeko` 做 >2GB 的 FASTA
  随机访问，若落到 ILP32 会静默截断偏移。test_package 逐条断言 OHOS PC 上
  `sizeof(void*)` / `sizeof(long)` / `sizeof(off_t)` / `sizeof(int64)` 均为 8。
- 任务路径：【知识库扩展】。新增知识条目见
  `knowledge/drafts/DRAFT-libgclib-0.12.8-*.{md,kv}`。
- 上游 tag 带 `v` 前缀（`v0.12.8`），URL 用
  `archive/refs/tags/v0.12.8.tar.gz`，`strip_root=True` 拉平 `gclib-0.12.8`。

---

**编译结束**: 2026-09-20
**最终状态**: built
