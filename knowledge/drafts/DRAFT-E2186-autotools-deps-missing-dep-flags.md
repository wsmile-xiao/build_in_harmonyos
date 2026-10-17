# DRAFT-E2186：autotools 配方漏掉 `AutotoolsDeps` 时依赖 flags 静默缺失

> Contributor: Awstme | Status: Draft | Updated: 2026-09-11
> Source: debfoster 2.8 适配（`conan create` G2 轮，configure 全绿、make 首错）

## 背景

debfoster 2.8（autotools，单一可执行文件）依赖 `gc/8.2.12`：`configure.ac` 用
`AC_CHECK_LIB(gc, GC_malloc)` 探测，`src/error.c` 里 `#include <gc/gc.h>`。
配方的 `generate()` 起初只写了 `AutotoolsToolchain(self).generate()`（与仓库模板
`templates/conanfile-autotools.py.tmpl` 一致）。结果 configure 一路成功，`make` 在
第一个消费者文件上失败。

## 现象

`configure` 看起来完全正常，连依赖探测都是绿的：

```text
checking for GC_malloc in -lgc... yes
configure: creating ./config.status
...
```

失败发生在 `make` 的首个翻译单元：

```text
/storage/.../b/src/error.c:3:10: fatal error: 'gc/gc.h' file not found
#include <gc/gc.h>
         ^~~~~~~~~
make[2]: *** [Makefile:425: error.o] Error 1
```

而同一轮的编译命令行里没有任何依赖的 include/lib 路径：

```text
/data/service/hnp/bin/clang -DHAVE_CONFIG_H -DVAR=\"//var\" -DETC=\"//etc\" \
  -DLOCALEDIR=\"//share/locale\" -I. -I/storage/.../b/src   -DNDEBUG -Wall -O3 \
  -MT error.o -MD -MP -MF $depbase.Tpo -c -o error.o /storage/.../b/src/error.c
```

只有 `-I.` 与 `-I<build>/src`（来自 `AM_CPPFLAGS`/automake 自身），没有任何
`-I<gc>/include`；`CFLAGS` 里也只有 `-DNDEBUG -Wall -O3`，即
`AutotoolsToolchain` 自己产出的部分。

## 根因

Conan 2 把 autotools 集成拆成两个独立 generator：

| generator | 负责内容 | 落到哪里 |
| --- | --- | --- |
| `AutotoolsToolchain` | 编译器、基础 CFLAGS/CXXFLAGS/LDFLAGS、`configure_args`、`--prefix/--bindir/--libdir/...` | `conanautotoolstoolchain.sh` |
| `AutotoolsDeps` | requirements 的 `-I`/`-L`/`-l`（`CPPFLAGS`/`LDFLAGS`/`LIBS`） | `conanautotoolsdeps.sh` |

只生成前者时，依赖的 include/lib 路径根本不会被写进环境，configure 自然拿不到。

**为什么失败点被推迟**：`AC_CHECK_LIB(gc, GC_malloc)` 是纯**链接**探测——它只编译一个
调用 `GC_malloc` 的 `conftest.c`（不 include 任何 gc 头，只需一个隐式声明）并与
`-lgc` 链接。`LDFLAGS` 里虽然也没有 `-L<gc>/lib`，但该探测仍能通过，因为
`libgc.a` 在设备的默认库搜索路径或 conan 注入的链接行上可达，于是 configure
打印 `checking for GC_malloc in -lgc... yes` 并 rc=0。真正的头文件需求直到
`make` 编译 `src/error.c` 才被触发。

这条链路的危险之处在于：**configure 的 rc=0 + 依赖探测 yes 是一个假绿信号**，
它同时掩盖了「`-I` 缺失」和「`-L` 缺失」两个缺陷——后者在链接 `debfoster` 时才会
以 `undefined reference to GC_malloc` 形式再次出现。

## 修复

`generate()` 里两个 generator 都生成，顺序为先 Toolchain 后 Deps：

```python
def generate(self):
    AutotoolsToolchain(self).generate()
    AutotoolsDeps(self).generate()
```

仓库内共 177 个 autotools 配方已使用 `AutotoolsDeps`，可参照
`archives/g/guile/2.2.7.1/conanfile.py`（它同时依赖 `gc`）：

```python
def generate(self):
    tc = AutotoolsToolchain(self)
    tc.generate()

    deps = AutotoolsDeps(self)
    deps.generate()
```

## 为什么容易漏

`templates/conanfile-autotools.py.tmpl` 的 `requirements()` 是空的：

```python
def requirements(self):
    # All dependencies MUST use @ohpcd/stable format (R27)
    # self.requires("openssl/1.1.5w@ohpcd/stable")
    pass
```

模板里没有依赖，所以只写 `AutotoolsToolchain` 也能通过模板自带的示例。一旦适配者
按实际依赖补上 `self.requires(...)`，就必须同时补 `AutotoolsDeps`，而模板没有任何
提示（模板的 `generate()` 里只有 `tc.generate()`）。这与仓库模板的另几处「教错」
面同族（见 workflow 第 5.3 节的模板缺陷条目）。

## 与既有条目的差异

E467 讲的是 `AutotoolsDeps` **存在**时的另一种失败：它把依赖闭包写进 `LIBS`，
autoconf 最早的 `AC_PROG_CC` 交叉编译判定会沿用这些 `LIBS` 去链接 `conftest`，
于是本应只跑空 `main` 的探测变成需要加载整条共享依赖闭包，任一库不可加载就在
configure 阶段以 rc=77 失败。

本条是**相反方向的缺口面**：

- E467：Deps 在 → configure 过早变严，rc=77，错误位置在 configure；
- 本条：Deps 缺 → configure 反而全绿（`-l` 探测假通过），错误位置在 make。

两者的判据不同（E467 查 `config.log` 里 conftest 的链接命令；本条查编译行里
有没有依赖 `-I`），修复方向也不同（E467 修可加载性；本条补 generator）。
因此不能互相替代，也不能用 E467 的「不要加 Deps」思路处理本模式。

## 判读命令

```sh
# 1) 编译行里到底有没有依赖 include
grep -n -- '-I.*gc' reports/conan-create.log

# 2) 两个 generator 脚本是否都生成（build 目录随轮次重建，用 glob 定位）
find "$(ls -d "${CONAN_HOME:-$HOME/.conan2}"/p/b/debfo*/b | head -1)" \
     -name 'conanautotools*.sh'

# 3) 依赖探测是否"假通过"
grep -n 'checking for .* in -l.*\.\.\. yes' reports/conan-create.log
```

## 复现

debfoster 2.8 的 `archives/d/debfoster/2.8/conanfile.py`：删掉
`AutotoolsDeps(self).generate()` 一行即确定性复现（同一 SHA、同一 profile）。
