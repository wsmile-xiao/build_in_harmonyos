# DRAFT-jaula-1.4.0 — automake 1.10.x（本包由 1.10.1 生成）的 `DEFAULT_INCLUDES` 不含 `$(top_srcdir)`：公开头自引用 `<pkg/x.h>` 的老包在 VPATH 构建下必挂

## 问题

jaula 1.4.0（autoconf 2.61 + automake 1.10 生成，2009 年发布）在 conan 真机构建中，
 configure 全部通过后，编译第一个源文件即失败：

```
libtool: compile: clang++ -DHAVE_CONFIG_H -I. -I<...>/b/jaula -I.. \
  -I<...>/flex.../p/include -DNDEBUG -stdlib=libc++ -fPIC -O3 \
  -c <...>/b/jaula/jaula_bad_data_type.cc -o jaula_bad_data_type.o
<...>/b/jaula/jaula_bad_data_type.h:32:10: fatal error:
  'jaula/jaula_exception.h' file not found
```

关键线索有两处：

1. 编译行里的 `-I` 只有 `.`、`$(srcdir)`（= `b/jaula`）、`-I..`（= `build-release`），
   **没有任何一层包含名为 `jaula/` 的目录**——而 `<jaula/jaula_exception.h>` 必须从
   "含 `jaula/` 子目录的那一层"（即源码根 `b/`）才可解析；
2. `build-release/jaula/` 确实存在，但里面只有 `Makefile`、`.deps/`、`.libs/`，没有头文件。

`grep "^DEFAULT_INCLUDES" build-release/jaula/Makefile` 给出确定性证据：

```
DEFAULT_INCLUDES = -I. -I$(srcdir) -I$(top_builddir)
```

而上游 `jaula/Makefile.am` 里 `AM_CPPFLAGS` **被显式删除**（文件内注释：
`# AM_CPPFLAGS removed as required for bug 1827161`），所以没有任何地方补 `-I$(top_srcdir)`。

## 根因

automake 子目录规则里，编译命令的包含路径来源为：

```
COMPILE = $(CXX) $(DEFS) $(DEFAULT_INCLUDES) $(INCLUDES) \
          $(AM_CPPFLAGS) $(CPPFLAGS) $(AM_CXXFLAGS) $(CXXFLAGS)
```

- automake 1.10.x（本包实测由 1.10.1 生成） 把 `DEFAULT_INCLUDES` 生成为 `-I. -I$(srcdir) -I$(top_builddir)`，
  **不含 `$(top_srcdir)`**；
- 2005–2012 年代一批 C/C++ 包的公开头彼此写成 `#include <pkg/xxx.h>`（安装态布局的
  镜像写法），依赖"源码根在 -I 集合里"这一隐含前提；
- **同目录（in-tree）构建时该前提被意外满足**：`top_builddir` 展开为 `..`，正好指向源码根；
- conan 的 `basic_layout`/`cmake_layout` 都是 out-of-source，`top_builddir` 指向构建树，
  这一层 `-I` 就消失了。上游若像 jaula 一样删了/没写 `AM_CPPFLAGS`，就没有任何东西补回来。

即：**这不是 OHOS/交叉编译问题，是"老 automake + VPATH + 自引用公开头"三者交叉的通用坑**，
在任何 out-of-source 构建（含 CI worker）上同样成立。

## 方案（首选：make 命令行注入，零改上游）

`AM_CXXFLAGS` 出现在 `COMPILE` 行且 automake 默认不赋值，而 **make 命令行变量的优先级高于
Makefile 内的赋值**，因此可以在配方里精确注入，在通过下文第 4 步取证（上游对被覆盖变量无 `+=` 追加、无既有赋值）的前提下不丢既有 flags，也不覆盖
`CPPFLAGS` 里来自 `AutotoolsDeps` 的依赖 `-I`：

```python
autotools = Autotools(self)
autotools.make(args=["-C", "jaula", "-j1",
                     "AM_CXXFLAGS=-I{}".format(self.source_folder)])
```

要点：
- 传 `self.source_folder`（源码根），不是 `self.build_folder`；
- 若失败目标在多个子目录，把 `-C <subdir>` 与 `AM_CXXFLAGS` 一并按子目录传入；
- 用 `AM_CXXFLAGS`（纯 C++ 工程）；含 C 源时用 `AM_CFLAGS` 或直接 `DEFAULT_INCLUDES=...`
  整串覆盖。

**第 4 步取证（用这个修法前必做，否则会制造新缺陷）**：make 命令行的 `var=value` 会
**整体作废** Makefile 内对该变量的所有 `+=` 追加（见
`经验文档/B草稿库/DRAFT-PKG-VER-make-commandline-override-kills-plus-equals`）。
注意引用边界：那条草稿的**主结论**（env 与命令行的选择面）自带 `safety_boundary` 排除了
autoconf/automake 生成的包；本处只取它揭示的那半条 **GNU make 通用语义**——命令行赋值优先级高于
Makefile 内赋值并会作废该变量的 `+=` 追加——作为"能不能覆盖这个变量"的前置判据，不要把它当成
对本包 flag 注入面的完整结论。
所以必须先 `grep` 上游 `Makefile.am`/`Makefile.in`，确认被覆盖变量没有 `+=`、也没有自带既有值。
本包取证结果：`grep -c AM_CXXFLAGS jaula/Makefile.am` = 0，且 `jaula/Makefile.in` 只在
`CXXCOMPILE`/`CXXLINK` 里引用 `$(AM_CXXFLAGS)`、从无赋值行 ⇒ 覆盖不丢任何东西。
若目标变量本身带值（如 `CFLAGS`/`CPPFLAGS`），必须把既有值一并重述进命令行。

## 验证

鸿蒙 PC（HarmonyOS 4.x，aarch64，clang 15.0.4，conan 2.29.1）真机：

```
$ conan create archives/j/jaula/1.4.0 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 编译行出现 -DNDEBUG -I<...>/b -stdlib=libc++（源码根已注入）
# jaula/ 子目录 16 个手写 `.cc` + flex 现场生成的 `jaula_lexan.cc` = **17 个 TU** 全部编译通过（`examples/` 的 2 个 `.cc` 不在构建范围） → libjaula.a 产出 → 打包成功
# test_package 消费者测试：test_parse 14/14、test_corpus 11/11、test_errors 7/7（共 32 断言）
CREATE_RC=0
```

反证留存：同一配方去掉 `AM_CXXFLAGS` 后首错逐字复现（日志
`~/tmp/uc2/hw-9/logs/build4.log` 第 235 行）。

## 适用边界

成立条件（三条同时满足）：
1. conan 走 out-of-source / VPATH 构建（默认如此）；
2. `configure`/`Makefile.in` 由 automake 1.10.x（本包实测 1.10.1） 一类老版本生成，其 `DEFAULT_INCLUDES`
   不含 `$(top_srcdir)`；
3. 头文件自引用带 `<pkg/>` 前缀，且上游没有写 `AM_CPPFLAGS = -I$(top_srcdir)`。

不适用 / 不要照抄：
- 上游已写 `AM_CPPFLAGS = -I$(top_srcdir) ...`：那属于另一条机制
  （`DRAFT-10251-libnfc-tools-1.8.0-automake-per-target-cppflags-empty-override`：
  写了但被**空的 per-target** `*_CPPFLAGS` 顶掉），签名与修法都不同，混引会被复核打回；
- 构建系统压根不支持 VPATH（规则里无 `$(srcdir)`，报 `No rule to make target 'x.c'`）：
  走 in-source layout，见 `DRAFT-kakasi-2.3.6-autotools-relative-includes-vpath`。

## 反例

- 只在宿主机 `./configure && make`（同目录）复现过的人，会以为"这包没问题"，到 conan/CI
  必挂——同目录构建掩盖了缺失的那层 `-I`，因此**本地手跑通过不能作为该机制不成立的证据**。
- 把 `-I` 加进 `CPPFLAGS`（configure 命令行）不是等效解法：会覆盖 `AutotoolsDeps` 注入的
  依赖 `-I`，把本问题换成"依赖头找不到"。

## 限制

- `AM_CXXFLAGS` 命令行覆盖只作用于被显式调用的那次 `make`；若配方改跑顶层 `make`
  （含全部 SUBDIRS），需按目标目录分别传，或直接给 `make` 传
  `DEFAULT_INCLUDES="-I. -I$(srcdir) -I$(top_builddir) -I$(top_srcdir)"`。
- 本机制只解"编译期找头"，不解运行时；若同类包还把 `<pkg/x.h>` 安装到非标准层级，
  消费者侧仍需按 `package_info()` 闭包补齐。
