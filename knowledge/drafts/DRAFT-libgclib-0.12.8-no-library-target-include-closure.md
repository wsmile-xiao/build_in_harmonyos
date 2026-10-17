# DRAFT：上游没有「库」这个产物 —— 手写 Makefile 只编演示程序时，适配必须自定库边界；发运头文件取「已编译 TU 的 quoted-include 闭包」

- **软件**：gclib 0.12.8（`gpertea/gclib`，GFFread / StringTie 的共同底座）
- **触发工具**：`make` / `clang++` / `conan`
- **阶段**：configuration（包边界定义）
- **严重度**：2
- **分类**：build-system, packaging, make, conan, portability, headers
- **状态**：UNMATCHED —— 待人工/AI 复核后 promote 为 E 条目
- **来源**：`archives/l/libgclib/0.12.8` 适配（PR #11371，任务 #8205）

---

## 错误特征

这一类问题**不会以「构建报错」的形式出现**——上游本来就编得过，只是编出来的
不是库。真正的痛点在适配者一侧：找不到任何官方的「库边界」可以照抄，于是
三种典型错误会在下线很久之后才暴露：

| 现象 | 真正的原因 |
|------|-----------|
| `conan create` 全绿，消费者一 `#include <GFastaFile.h>` 就报 `No such file` | 发运头文件集合拍脑袋定的，漏掉了消费者真正需要的头 |
| 消费者 `#include` 编得过，链接时报 `undefined reference to translateCodon` | 只拍了上游 `OBJS` 那 4 个 TU，漏掉了 `codons.cpp`/`gdna.cpp` 等其余 TU |
| 发运出去的某个头**单独包含就编译失败** | 该头对应的 TU 根本没被编译过（依赖未随包发布的第三方库），头是「顺手拷进去的」 |
| 库按 `-std=c++11` 编得绿，消费者按 profile 默认的 `-std=c++17` 一 `#include` 就炸：`error: exception specification in declaration does not match previous declaration` | 上游只在 c++11 下编过，某些"c++11 下被编译器放过"的头文件违规在 c++17 下变成硬错误（如声明/定义的 `noexcept` 不一致）。**给消费者加 `-fno-exceptions` 不解决问题** —— c++17 下 `noexcept` 已是函数类型的一部分 |
| 只跑了一趟编译的 test_package「CI 绿」，真实消费者却编不过 | 只跑了 c++11（上游的标准）那一趟。**「上游编得过」与「消费者编得过」是两件事**，必须按消费者实际用的标准再跑一趟 |

识别信号（`grep` 层面，三条同时成立即命中）：

```bash
# (1) 没有任何库归档 / 共享库 / libtool 规则
grep -nE '^[^#]*[[:alnum:]_$/.-]+\.(a|so|dylib)[[:space:]]*:' Makefile   # 期望：空
grep -nE 'shared|libtool|-shared|ar[[:space:]]+rcs' Makefile             # 期望：空
# (2) 没有 install 规则
grep -nE '^install(-[[:alnum:]]+)?[[:space:]]*:' Makefile                # 期望：空
# (3) 有一个 .o 列表变量，且它只被「演示程序 / 工具」消费
grep -nE '^[[:space:]]*(all|OBJS)[[:space:]]*[:=]' Makefile
#   → all: htest        （目标是带 main() 的演示程序）
#   → OBJS := GBase.o GStr.o GArgs.o GResUsage.o
```

---

## 触发条件

三条同时成立：

1. 上游仓库根**只有一份手写 Makefile**（没有 CMake / autotools / meson 等能推导出
   install 集合的构建系统）；
2. 该 Makefile **没有库目标、也没有 install 规则**；
3. 存在 `OBJS := ...` 这类 `.o` 列表变量，其消费者是**下游程序**而不是本仓的库
   —— 也就是「把 `.o` 直接链进自己的可执行文件」这种用法。

满足这三条的包，适配者面对的其实是一个**规范缺失**问题：上游从未回答
「这个库由哪些文件组成」，而这个答案又必须由本包给出。

gclib 0.12.8 的仓库根 Makefile 全貌（去掉注释与变量展开）：

```make
OBJS := GBase.o GStr.o GArgs.o GResUsage.o
BASEFLAGS := -std=c++11 -Wall -Wextra ${INCDIRS} $(MARCH) -D_REENTRANT -fno-exceptions -fno-rtti
LIBS := -lz

all: htest
```

`htest` 是一个带 `main()` 的基准/演示程序。GFFread / StringTie 的既有用法是把
这些 `.o`（乃至全部 16 个）**直接链进自己的可执行文件**，所以上游从来没有
「安装一批头 + 一个 .so」这种需求，也就没有对应的规则。

---

## 根因分析

### (1) 上游没有回答「库由哪些文件组成」

CMake 的 `install(TARGETS ...)` / autotools 的 `include_HEADERS` / `lib_LTLIBRARIES`
都在**上游仓库里**写死了「装什么」。一旦这些都没有，问题就从
「把上游的 install 规则翻译成 Conan 的 package()」变成了
**「先决定这个库是什么」**。这是两个不同量级的问题：前者是机械翻译，
后者是一个需要论证的设计决策。

### (2) tarball 里的文件**不等于**库的组成

`gclib` 的 release tarball 里有 22 个 `.cpp`，但只有 16 个属于库：

| 类别 | 文件 | 理由 |
|------|------|------|
| 缺未随包发布的第三方头 | `GBam.cpp` | 需要 htslib 的 `kstring.h` / `sam.h` / `bam.h`；htslib **不随包发布**，也没有任何 pkg-config / CMake 探测把它变成显式选项 |
| 同上 | `gdimg.cpp` | 需要 libgd 的 `gd.h`，同样不随包发布、无探测 |
| 同上 | `gff.cpp` | 需要 boost 的 `boost/crc.hpp`，同样不随包发布、无探测 |
| 带 `main()` 的演示程序 | `htest.cpp` / `mdtest.cpp` / `gtest.cpp` | 手工演示程序，不是库代码 |
| **库翻译单元** | **其余 16 个** | `GBase` `GStr` `GArgs` `GResUsage` `GThreads` `gcdb` `GCdbYank` `gsocket` `gstopwatch` `proc_mem` `codons` `gdna` `GAlnExtend` `GFastaIndex` `GFaSeqGet` `GapAssem` |

关键点：这三条「编不过」的理由**不是本地环境缺东西**，而是**上游把可选功能的
依赖留在了树外**。这跟「装个 htslib 就能编」是不同的结论 —— 上游没有任何开关
能让 `GBam.cpp` 在没有 htslib 的情况下退化编译，也没有任何探测能在
configure 期把它变成 `--with-htslib` 之类的选项。所以正确处置是
**如实排除并写明理由**，而不是试图把它编出来。

### (3) 发运头文件集合可以由「已编译 TU」推导出来 —— 这是可验证的

一旦 (2) 定下了 TU 集合，头文件集合就不该再靠连猜：取这 16 个 TU 的
**quoted-include 传递闭包**（`#include "..."` 形式的本地头），得到 24 个：

```
GBase.h GStr.h GArgs.h GResUsage.h GThreads.h gcdb.h GCdbYank.h gsocket.h
gstopwatch.h proc_mem.h codons.h gdna.h GAlnExtend.h GFastaIndex.h
GFaSeqGet.h GapAssem.h GFastaFile.h
GList.hh GVec.hh GHash.hh GHashMap.hh khashl.hh wyhash.h xxhash.h
```

这个取法有一条**结构性保证**：闭包里的每个头都被某个**被编译的 TU** 直接或
间接包含过。因此「发运了却编不过的头」在构造上就不可能存在 —— 不是靠人工核对，
而是靠集合的定义方式。

这条保证在别的库里经常不成立。典型反例是"上游有一批头是给别的子库用的"，
顺手拷进 package 后消费者一包含就炸。用闭包取集合能一次性消灭这类问题。

（另外三个口径上的坑，gclib 全部踩过，写在这里当检查清单：
`#include "config.h"` / `#include <config.h>` 在源码树里**并不存在**，
但受 `HAVE_CONFIG_H` 守卫；`"windows.h"` / `"psapi.h"` 受 `_WIN32` 守卫。
受守卫挡住的 include **不构成依赖**，但扫描闭包时如果只看字面 include 就会
把它们算进去。正确做法是跟着预处理条件走：上游 Makefile 不定义
`HAVE_CONFIG_H`，本包也就不定义。）

---

## 解决方案

### 配方侧：两个集合 + 一道校验

```python
_LIB_TUS = (  # (1) 翻译单元集合：逐个试编后能成功的全部 .cpp
    "GBase", "GStr", "GArgs", "GResUsage", "GThreads", "gcdb", "GCdbYank",
    "gsocket", "gstopwatch", "proc_mem", "codons", "gdna", "GAlnExtend",
    "GFastaIndex", "GFaSeqGet", "GapAssem",
)
_PUBLIC_HEADERS = (  # (2) 发运集合 = 上述 16 个 TU 的 quoted-include 闭包
    "GBase.h", "GStr.h", "GArgs.h", "GResUsage.h", "GThreads.h",
    "gcdb.h", "GCdbYank.h", "gsocket.h", "gstopwatch.h", "proc_mem.h",
    "codons.h", "gdna.h", "GAlnExtend.h", "GFastaIndex.h", "GFaSeqGet.h",
    "GapAssem.h", "GFastaFile.h",
    "GList.hh", "GVec.hh", "GHash.hh", "GHashMap.hh",
    "khashl.hh", "wyhash.h", "xxhash.h",
)
```

编译与链接（上游没有库规则，两种形态都自己声明）：

```python
flags = "-std=c++11 -D_REENTRANT -fno-exceptions -fno-rtti -O2"
#   ^ 前四项照抄上游 BASEFLAGS；-O2 对应 profile 的 build_type=Release。
#     上游的 -Wall -Wextra 是诊断项，不进产物，不施加。
for tu in _LIB_TUS:  # 逐个编译，-fPIC
    ...
# shared: clang++ -shared -pthread -Wl,-soname,libgclib.so -o libgclib.so *.o
# static: llvm-ar rcs libgclib.a *.o
```

`package()` 里加**逐条数校验**：

```python
for header in self._PUBLIC_HEADERS:
    copy(self, header, src=..., dst=...)
staged = <实际落地的头数量>
if staged != len(self._PUBLIC_HEADERS):
    raise ConanException(...)   # 静默少装 = 消费者侧才炸，那时已经晚了
```

还有一个**发运之外**的动作：库编得过 ≠ 消费者编得过，所以配方里要带一个
**修头文件**的补丁（见下一节）：

```python
exports_sources = "patches/*"

def source(self):
    get(self, **self.conan_data["sources"][self.version], strip_root=True)
    patch(self, patch_file="patches/0001-glist-move-ctor-noexcept-declaration.patch",
          base_path=self.source_folder)
```

### `-fno-exceptions` 不是万能挡箭牌：C++11 能豁免的诊断，C++17 豁免不了

上游 `BASEFLAGS` 带 `-fno-exceptions -fno-rtti`，而 gclib 全库**零 `throw`、
零 `dynamic_cast`/`typeid`**，所以它们只影响异常表与 RTTI 元数据的生成，
不影响行为。看起来可以放心跟着上游走。这里却连踩两级：

**第一级（当时以为已经解决）**：`GList.hh` 的移动构造声明与定义异常规格
不一致 —— 声明没有 `noexcept`，定义有：

```
GList.hh:101:5: note: previous declaration is here
    GList(GList<OBJ>&& list); //move constructor
GList.hh:375:34: error: exception specification in declaration does not match previous declaration
template <class OBJ> GList<OBJ>::GList(GList<OBJ>&& other) noexcept:
```

只按 C++11 看，`-fno-exceptions` 确实能压掉这条诊断（clang 在异常关闭时
跳过声明/定义等价性检查）—— 上游 16 个 TU 就是这么编过的。于是当时的处置是
把开关经 `cpp_info` 发布给消费者，并在 test_package 里从依赖方取用：

```python
self.cpp_info.cxxflags = ["-fno-exceptions", "-fno-rtti"]
```

**第二级（开关救不了的那一半）**：这个处置**只在 C++11 下成立**。C++17 起
`noexcept` 已经是**函数类型的一部分**，等价性检查不再受 `-fno-exceptions`
影响。而 OHOS 消费者默认 `-std=c++17`。CI build #53438 的日志把两趟并排
放在一起，结论一目了然：

```
# 同一份 test_package，只差 -std 一个参数
clang++ -std=c++11 -O1 -fno-exceptions -fno-rtti ... → checks=83 failures=0
clang++ -std=c++17 -O1 -fno-exceptions -fno-rtti ... → GList.hh:375:34: error:
    exception specification in declaration does not match previous declaration
```

所以正确处置是**打补丁修头文件**，而不是靠编译开关绕：

```
patches/0001-glist-move-ctor-noexcept-declaration.patch
-    GList(GList<OBJ>&& list); //move constructor
+    GList(GList<OBJ>&& list) noexcept; //move constructor
```

改声明而不是删定义的 `noexcept`，是为了保留作者"移动构造不抛"的显式意图
（`GPVec` 基类是 `std::vector`，声明成 noexcept 才能让重分配走移动而非拷贝）。
24 个发运头里 `noexcept` 只出现在这一处，补丁是单点、可控的。

**教训**：`-fno-exceptions` 不是万能挡箭牌。把它当成"能豁免某条诊断"的
理由时，必须问清**它在哪个语言标准下豁免**——很多老代码的诊断放宽规则是
C++11 时代的产物，标准一升就失效，而 OHOS 消费者的默认标准恰好比上游新。
本包这一条最终是"补丁修源码"而不是"开关绕过去"，两者差别在于：开关绕
只对 c++11 消费者成立，补丁对两者都成立。

### 那两个开关仍然要发布，但理由换成了 ODR

修完头文件后 `-fno-exceptions` / `-fno-rtti` **仍然**经 `cpp_info` 发布 ——
只是理由不再是"绕开诊断"，而是：gclib 是模板密集库，`GList<OBJ>`/`GVec<OBJ>`/
`GHash<...>` 这些模板**同时**在库的 16 个 TU 里和消费者的 TU 里实例化（24 个
头全部发运，消费者必然包含它们）。两侧开关不一致，等于同一实体在不同 TU 里
有两份语义不同的定义。这本来就是上游 `BASEFLAGS` 给下游定的 ABI 假设。

test_package 从 `dependencies["libgclib"].cpp_info.cxxflags` 取用而不是自己
写死，顺带验证依赖方真的发布了这两个开关。

### 同名不同签名的两个 `class GHash` —— 24 个头无法同处一个 TU

「发运头文件集」这个契约里还藏着一个更硬的约束：这 24 个头**必须拆成两个
TU** 才能各自被包含。

| 头 | 定义 | 谁包含它 |
|----|------|---------|
| `GHash.hh` | `template <class OBJ> class GHash`（char* 键的旧式哈希表） | `GapAssem.h:6` |
| `GHashMap.hh` | `template <class V, class Hash=…, class Eq=…, typename khInt_t=uint64_t> class GHash` | `GFastaIndex.h` ← `GFaSeqGet.h` |

两者 headerguard 不同、名字却相同，任何 TU 同时包含就是硬错误：

```
GHash.hh:21:1: error: too few template parameters in template redeclaration
template <class OBJ> class GHash {
GHashMap.hh:389:1: note: previous template declaration is here
```

所以「N 个发运头都能被消费者包含」这条契约**不能**用一个
「把所有头 #include 一遍」的 TU 来证 —— 那样测出来的是「上游头之间是否
互斥」，不是「每个头是否自洽」。正确写法是按**编译簇**（compilation
cluster，同名标识符互斥的传递闭包）分组，每个簇一个 TU：

```
GHashMap 簇：GFastaIndex.h GFaSeqGet.h GHashMap.hh khashl.hh wyhash.h xxhash.h
GHash    簇：GHash.hh GapAssem.h
公共       ：GBase.h GStr.h GArgs.h ... GList.hh GVec.hh GFastaFile.h
```

（`-fsyntax-only` 逐头单独编译那种写法不受影响 —— 一个头一个 TU，本来就
不可能撞上。踩坑的是「把所有头堆进同一个 TU」这种图省事的写法。）

但**真正需要证明的**是另一件事：库按 `-std=c++11` 编、而 OHOS profile 的
`compiler.cppstd` 是 **17**，两者能不能互链？gclib 在**链接层**的答案是可以 ——
gclib 全库零 `throw`、零 `dynamic_cast`/`typeid`，不存在跨标准的 ABI 落差。
这个结论不该靠推理，而该靠实测：本包的 `test_package` 用**同一份消费者源码**
在 `-std=c++11` 与 `-std=c++17` 下**各编一次、各跑一次**，两次都必须链接成功
且 83 条断言全绿。

而这趟实测**立刻证明了「链接层没问题」不等于「头文件层没问题」**：c++11 那趟
83 条全绿，c++17 那趟第一行就死在 `GList.hh:375`（见上文「`-fno-exceptions`
不是万能挡箭牌」）。这一对双标准编译的意义就在这里 —— 只跑 c++11 会得到一个
"CI 绿"的假象，而 OHOS 消费者默认用的正是 c++17。

### 「零第三方依赖」也要论证，不能默认

上游 Makefile 有 `LIBS := -lz`，看起来像 zlib 依赖。但它服务的是本包**不编译**的
`gff.cpp`（boost 路径）与 `GBam.cpp`（htslib 路径）；`GCdbYank.h` 里
`#include <zlib.h>` 与整个 `GCdbZFasta` 类都在 `#ifdef ENABLE_COMPRESSION` 里，
而上游 Makefile **没有定义**这个宏。所以本包零第三方依赖。

这是一个值得写进条目的模式：**上游 Makefile 的 `LIBS` 是「所有目标之和」，
不是「库目标的依赖」**。照抄 `LIBS` 会引入多余的依赖，而且很可能引入一个在
OHOS 上根本不需要（甚至没有）的包。

---

## 验证命令

```bash
# 1) 判定上游有没有库产物（三条判据全空即命中本条目）
grep -nE '^[^#]*[[:alnum:]_$/.-]+\.(a|so|dylib)[[:space:]]*:' Makefile   # 空
grep -nE '^install(-[[:alnum:]]+)?[[:space:]]*:' Makefile                # 空
grep -nE 'shared|libtool|-shared|ar[[:space:]]+rcs' Makefile             # 空
grep -nE '^[[:space:]]*(all|OBJS)[[:space:]]*[:=]' Makefile              # all: htest / OBJS := ...

# 2) 数「哪些 TU 编得过」——失败的那几个就是边界之外，并记录失败原因
for f in *.cpp; do
  clang++ -std=c++11 -D_REENTRANT -fno-exceptions -fno-rtti -I. -c "$f" -o /dev/null 2>&1 \
    | grep -m1 -E 'fatal error|No such file' && echo "OUT: $f"
done

# 3) 算 include 闭包（发运集合）
grep -hE '^[[:space:]]*#[[:space:]]*include[[:space:]]*"' *.cpp *.h *.hh \
  | sed -E 's/.*"([^"]+)".*/\1/' | sort -u

# 4) 消费者侧实证：24 个头逐个单独包含（一个头一个 TU，不能用「全部堆一个 TU」代替）
for h in <24 个头>; do
  printf '#include "%s"\nint main(){return 0;}\n' "$h" \
    | clang++ -std=c++11 -fno-exceptions -fno-rtti -I<include> -fsyntax-only -x c++ - \
    || echo "BAD HEADER: $h"
done

# 4b) 顺带查出「同名不同签名的声明」——把同一批头两两配对会炸出 D 组那种硬错误
grep -hoE 'class[[:space:]]+[A-Za-z_][A-Za-z0-9_]*' *.h *.hh | sort | uniq -d
    # gclib 命中：GHash（GHash.hh 的 `template<class OBJ>` vs
    #                   GHashMap.hh 的 `template<class V,class Hash,...>`）

# 4c) **把每个头再按 c++17 编一遍** —— 上游只按 c++11 编过，这一步才是
#     "消费者视角"。c++11 全绿不代表 c++17 全绿（noexcept 在 c++17 进了函数类型）
for h in <24 个头>; do
  printf '#include "%s"\nint main(){return 0;}\n' "$h" \
    | clang++ -std=c++17 -fno-exceptions -fno-rtti -I<include> -fsyntax-only -x c++ - \
    || echo "BAD HEADER (c++17): $h"
done
    # gclib 未打补丁时命中 GList.hh:
    #   GList.hh:375:34: error: exception specification in declaration does not
    #   match previous declaration  (:101 的声明少了 noexcept)
    #   —— 注意：加不加 -fno-exceptions 都一样报错，c++17 下不再豁免

# 5) 单点定位"哪一行是那个不一致的 noexcept"（补丁就是改这一行）
grep -n noexcept <闭包内所有头>     # gclib 全 24 个头只有 GList.hh:375 一处
```

`gclib` 实证结果：22 个 `.cpp` → **16 个库 TU**（排除 3 个缺第三方头的 +
3 个带 `main()` 的），闭包 **24 个头**，零第三方依赖；上游测试数 **0**
（无 `test/` 目录、无 CI；朴素 `assert(` 扫描的 8 处命中经逐条核验全部不是
用例：`gff.cpp` 3 处在注释里、`xxhash.h` 1 处是 `XXH_ASSERT` 宏定义、
`GHashMap.hh` 4 处是编译期 `static_assert`）。

---

## 禁止策略

| # | 禁止 | 原因 | 后果 |
|---|------|------|------|
| 1 | 删/注释/改后缀「编不过」的 TU（`GBam.cpp` 等）以求得「全都能编过」 | 它们属于「依赖未随包发布」，正确做法是如实排除并写明理由 | 篡改上游身份，边界不可复核，评审驳回 |
| 2 | 为了凑齐消费者想要的头而**凭空造**头（拼文件 / `touch` 占位 / 从别的版本拷） | 这类头从没被任何被编译的 TU 包含过，是典型的「发运了却编不过」 | 消费者一 `#include` 就失败，且失败点在消费者工程里，排查成本极高 |
| 3 | 为了让「c++11 库 + c++17 消费者」自洽而偷偷把库改高标准编译 | 正解是**实测**互链，并用双标准双跑证明 | 掩盖真实 ABI 事实，换个标准就复发 |
| 4 | 上游测试数为 0 时，把 `test_package` 的消费者断言跳过或降级 | 此时消费者断言是**唯一**的覆盖证据 | 通过率造假，rule4/rule12 不成立，PR 驳回 |
| 5 | 用一个 TU 把「全部发运头」`#include` 一遍来冒充「每个头都能被包含」 | 上游可能有两组**同名不同签名**的声明（gclib 的 `class GHash` × 2），堆进一个 TU 必炸，测出来的是头之间的互斥而非各自的自洽 | 消费者侧契约假通过；一旦跟着报错去删头，就变成「发运集合缩水」 |
| 6 | 在 `test_package` 里把上游 `BASEFLAGS` 的开关**漏掉**（或自己另写一套） | 消费者必须拿到与库一致的开关（模板两侧实例化的 ODR 要求）；漏掉即消费者视角失真 | 消费者工程里一 `#include` 就失败，而包本身「CI 绿」—— 最坏的一类假绿 |
| 7 | 用 `-fno-exceptions`（或把 `cppstd` 钉回 `c++11`）**绕开** `GList.hh` 的异常规格不一致，而不修头文件 | `-fno-exceptions` 只在 **C++11** 下豁免这条诊断；C++17 起 `noexcept` 是函数类型的一部分，该诊断照报。OHOS 消费者默认就是 c++17 | 「包里绿、消费者炸」的原样复发；把 `cppstd` 钉回 c++11 更糟 —— 那是拿消费者的语言标准为上游的 bug 买单 |
| 8 | 在 test_package 里只跑一趟编译（只跑 c++11，或只跑 profile 默认那一个标准） | 上游只在 c++11 下编过，「库编得过」与「消费者编得过」是两件事；c++11 全绿完全掩盖了 c++17 的头文件错误 | 得到"CI 绿"的假象，而真实消费者（OHOS profile 默认 c++17）一 `#include` 就失败 |

---

## 关联

- **E097** —— 上游无 configure、只有自定义 Makefile（bearssl 的 `mk/` + `conf/` +
  `SingleUnix.mk`）时须手工定义构建与安装。本条目更进一步：**上游连库产物都没有**，
  边界要自己划。
- **`DRAFT-fusion-1.3.3-cmake-no-install-rule-manual-package`** —— 有 CMake 但
  没有 install 规则，须手工 `package()`。与本条目同属「上游不提供安装元数据」家族，
  区别在于本条目连「库目标」都不存在。
- **`DRAFT-cqrlib-1.1.4-libtool-makefile-direct-compile`** —— libtool 工程直接
  `make` 编译；同属「上游不提供 Conan 可用的安装元数据」。
- **`DRAFT-gated-sublib-dual-archive-closure`** —— 双归档闭包的另一面：
  上游有**多个**产物时如何界定发运集合。本条目是它的极端情形（产物数为 0）。
- **E002** —— 本包的鸿蒙特有测试里，临时目录按 `$TMPDIR` → `$HOME` → `"."` 解析，
  不写死 `/tmp` / `/var/tmp`，即 E002 的消费者侧落实。

---

## 上游可提交性

本包**有一个补丁**（`patches/0001-glist-move-ctor-noexcept-declaration.patch`），
它修的是上游真实的头文件 bug，因此是一个**可以直接向上游提的 PR**：

- `GList.hh:101` 的声明缺 `noexcept`，而 `:375` 的定义有。这不是本适配引入的
  约束 —— 任何按 C++17 编译的下游都会撞上（clang 报
  `exception specification in declaration does not match previous declaration`），
  只是上游自己永远按 `-std=c++11 -fno-exceptions` 编，所以从没发现。
- 建议的上游改动就是本包补丁那一行；顺带值得上游自己跑一遍 `-std=c++17`
  的编译（CI 里加一趟），否则同类问题还会再出现。

另一个建议（不影响本适配，纯工程一致性）：补一个 install 规则（或 CMakeLists）。
`.o` 直接链接的用法在只有一个下游时可行，但 GFFread / StringTie 各自的链接命令
里都重复列出了同一批 `.o`，任何新增 TU 都要同步改多处。
