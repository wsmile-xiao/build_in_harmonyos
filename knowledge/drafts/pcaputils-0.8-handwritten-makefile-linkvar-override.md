# 手写 Makefile 交叉编译：链接变量名不是 `LDFLAGS`——从链接规则反推真实变量名并命令行覆盖（draft）

> Contributor: gcw_6YxinkyD | Status: DRAFT | Created: 2026-09-26
> 来源: pcaputils 0.8 适配（nongnu/Savannah，顶层 Makefile + 子目录 Rules.mk 递归 include，4 个 CLI + 内部 util.a，无 configure/CMake/install）

## 症状

上游是一份手写、递归 include 的 Makefile（无 autotools、无 CMake）：

```make
# Makefile
CC      = gcc
CFLAGS ?= -O2 -ggdb -Wall
CF_ALL  = $(CFLAGS) -Wextra -std=gnu99 -I.
LF_ALL  = -rdynamic -Wl,--as-needed -Wl,-z,defs     # ← 不是 LDFLAGS
LINK    = $(CC) $(LF_ALL) $(LF_TGT) -o $@ $^ $(LL_TGT) $(LL_ALL)
```

`src/Rules.mk` 里每个目标自己声明链接库：

```make
$(d)/pcapdump: LL_TGT := -lpcap
$(d)/pcapip:   LL_TGT := -lpcap -lJudy
```

在 OHOS 交叉编译时，**按 autotools 习惯传 `make LDFLAGS=-L... CPPFLAGS=-I...` 完全无效**——
链接行根本没有这两个变量的位置，依赖包的 `-L` 传不进去：

```
ld.lld: error: unable to find library -lpcap
ld.lld: error: unable to find library -lJudy
```

## 根因

1. **不要假设链接行用 `LDFLAGS`**。手写 Makefile 的链接标志变量名是作者自起的
   （本例 `LF_ALL`），而且它是 `=`（立即展开）赋值，不是 `?=`。
2. 但**命令行 `make VAR=value` 的优先级高于 Makefile 里的一切赋值**（无论是 `=` 还是 `?=`），
   所以 `LF_ALL=` 这种硬编码也能在命令行直接覆盖——**无需为了注入 `-L` 去改 Makefile**。
3. **`-l` 库是每目标私有的**（`LL_TGT := -lpcap -lJudy`），不要试图在顶层统一加；
   顶层只需要把 `-L` 搜索路径塞进链接行共用的那个变量。
4. 此类工程**没有 `install` 目标**，`make install` 不存在；产物（二进制）在 `src/`，
   必须在 Conan `package()` 里用 `copy()` 手工收。
5. `CC = gcc` 硬编码：和 `CC?=` 一样，命令行 `make CC=clang` 直接覆盖（R33 不依赖 PATH/环境）。

## 判据（不需要真机，读 Makefile 即可）

```sh
# 1) 找到真正的链接行，看它引用了哪个变量名（不是猜 LDFLAGS）
grep -nE '^[A-Z_]+[[:space:]]*=[[:space:]]*\$\(CC\)' Makefile */Rules.mk
#   → LINK = $(CC) $(LF_ALL) ...        ← 链接共用变量叫 LF_ALL
grep -nE 'LL_TGT|LF_TGT' src/Rules.mk    # ← 每目标私有 -l/-L

# 2) 那个变量是 ?= 还是 =（决定命令行能否覆盖；其实都能覆盖，= 也能）
grep -nE '^LF_ALL' Makefile

# 3) 有没有 install 目标
grep -nE '^install:' Makefile || echo "无 install → package() 必须 copy()"
```

## 修法（可复用配方模式，本案例 0 patch）

```python
def build(self):
    pcap = self.dependencies["libpcap"].cpp_info
    judy = self.dependencies["judy"].cpp_info
    inc  = " ".join(f"-I{d}" for d in pcap.includedirs)  + " " + \
           " ".join(f"-I{d}" for d in judy.includedirs)
    lib  = " ".join(f"-L{d}" for d in pcap.libdirs)      + " " + \
           " ".join(f"-L{d}" for d in judy.libdirs)
    # 关键：覆盖 Makefile 里真实的变量名（LF_ALL），而不是 autotools 的 LDFLAGS
    self.run(f"make CC=clang AR=llvm-ar -j1 "
             f"CFLAGS='-O2 {inc}' "
             f"LF_ALL='-rdynamic {lib} -Wl,--as-needed -Wl,-z,defs'",
             cwd=self.source_folder)

def package(self):
    for tool in ("pcapdump", "pcapip", "pcappick", "pcapuc"):   # 无 install 目标
        copy(self, tool, src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
```

要点：
- `-L<dep>/lib` 放进链接行共用变量（本例 `LF_ALL`），**在每目标 `-l` 之前**——GNU ld 单遍扫描，
  顺序错就是 `unable to find library`。
- `-I<dep>/include` 放进 `CFLAGS`（本工程编译行是 `$(CC) $(CF_ALL)`，`CF_ALL` 含 `$(CFLAGS)`）。
- 不要为了"加 LDFLAGS 位"去 patch Makefile（对比 zerofree 那条：它是单行 Makefile 连
  `$(CFLAGS)` 都没有、必须补变量；本工程链接行有现成的 `LF_ALL` 槽位，命令行覆盖即可）。

## 与现有条目的边界

- `DRAFT-zerofree-1.1.1-makefile-linkline-flags...`：那是 6 行单行 Makefile、链接行**只有**
  `$(CFLAGS)`、连 `-I/-L` 的槽位都没有，必须**改源码 Makefile** 补 `$(CPPFLAGS)/$(LDFLAGS)/$(LDLIBS)`。
  本条是递归/多目标 Makefile、链接行已有具名变量 `LF_ALL`，**命令行覆盖即生效、0 patch**；
  共性是"先读链接行再决定改不改 Makefile"，差异在是否需要补丁。
- `DRAFT-ohos-makefile-explicit-toolchain-and-install-vars`：讲 `CC`/`install` 命令缺失，
  不涉及"链接变量名不叫 LDFLAGS"这个发现过程。
- `DRAFT-cnrbtree-...-gcc-hardcode`：单讲 `CC=gcc` 覆盖；本条把它和链接变量名、每目标
  `-l`、无 install 打包成一个手写多目标 Makefile 的完整适配模式。

## 反直觉验证（真机实测，避免过度打补丁）

源码静态分析曾预判 `util/util.c` 里 `#include <execinfo.h>` + `backtrace()` 会在
musl/OHOS 编译失败（glibc-only 头），准备打 stub patch。**真机一次通过，无需 patch**——
OHOS 的 clang/musl 工具链实际提供了 `<execinfo.h>`。教训：glibc-only 头的预判先留着，
真机编一次再决定是否打补丁，不要凭本机 x86-64 glibc 经验提前改源码。

## 上游测试情况

pcaputils 0.8 上游无 tests/、无 `make check`（N=0）。可用性由 test_package 的消费者冒烟
验证：4 个二进制无参数运行，断言打印 `Usage:`（证明是 OHOS ELF、动态链接 libpcap/libJudy
成功、到达自身参数解析路径而非 loader 崩溃）。真机 conan create 全流程通过。
