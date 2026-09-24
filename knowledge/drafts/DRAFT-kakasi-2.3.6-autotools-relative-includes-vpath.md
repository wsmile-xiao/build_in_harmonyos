# DRAFT-kakasi-2.3.6 — autotools 相对 INCLUDES 在 out-of-source VPATH 下失效时改 in-source 构建

> 触发事件: kakasi 2.3.6 HarmonyOS PC 适配（shadow CI）
> 库类型: C 库 + 命令行工具（autotools + libtool，多目录 src/ lib/）

## 问题

kakasi 的 `lib/Makefile.am` 手写了相对头文件搜索路径：

```makefile
INCLUDES = -I.. -I../src
```

在 Conan 默认的 out-of-source VPATH 构建下（`basic_layout` 把源码放到 `b/`、
构建产物放到 `b/build-release/`），`make` 在 `build-release/lib` 里执行，
`-I../src` 被解析为 `build-release/src`（不存在），而真正的头文件在源码树
`b/src/`，于是编译 `lib/*.c` 时报：

```
libdict.c:50:10: fatal error: 'kakasi.h' file not found
#include "kakasi.h"
         ^~~~~~~~~~
```

注意：`src/` 目录的工具编译正常（单目录、头文件就在同目录），只有跨目录的
`lib/`（通过 `-I../src` 引用 `src/kakasi.h`）在 VPATH 构建下失效。

## 根因

kakasi 使用 `AUTOMAKE_OPTIONS = 1.4 no-dependencies`（automake 1.4 时代的
写法），`INCLUDES` 里手写的相对路径 `-I.. -I../src` 不会被 automake 映射到
源目录。规范写法应是 `-I$(top_srcdir) -I$(top_srcdir)/src`（用 `$(srcdir)`
变量），这样 VPATH 构建下也能正确指向源目录。这是上游老 Makefile.am 的
路径假设，不是库缺陷、也不是编译器差异。

## 方案

让 Conan 在源码树内构建（in-source），使 `-I../src` 相对路径回到源码目录：

```python
from conan.tools.layout import basic_layout

def layout(self):
    basic_layout(self)
    # 相对 INCLUDES (-I.. -I../src) 在 VPATH 构建下失效，改 in-source
    self.folders.build = "."
```

（与仓库内 zlib 配方同款处理。）其余 build() 里 configure 的路径相应改为
`self.build_folder` 下的 `configure`，make/make install 的 cwd 也随之落回源码树。

## 验证

- OHOS armv8 真机 `conan create`：`lib/*.c` 全部编译通过，`libkakasi.so` 生成成功。
- 之前 out-of-source 时 `src/` 工具编译通过、仅 `lib/` 报 `kakasi.h not found`，
  与"相对 INCLUDES 跨目录失效"的根因一致。

## 适用边界

- autotools 项目含多个源目录，且某个 `Makefile.am` 用相对路径 `-I.. -I../xxx`
  引用兄弟目录头文件；
- 在 Conan `basic_layout`（或任何 out-of-source/VPATH）构建下出现
  `fatal error: 'xxx.h' file not found`，但该头文件明明在源树里；
- 尤其常见于 `AUTOMAKE_OPTIONS = 1.x` 的老项目。

## 反例

- `Makefile.am` 已规范使用 `$(top_srcdir)`/`$(srcdir)`：VPATH 构建本就正确，无需 in-source；
- 单目录项目（头文件与源码同目录）：`-I.` 或默认搜索即可，通常无此问题；
- 若项目明确需要 VPATH（如 E434 copystamp 场景），不要机械改 in-source，应评估改
  `Makefile.am` 用 `$(top_srcdir)` 来保留 VPATH。

## 限制

- in-source 构建会把 `.o`/`.la` 等产物写进源码树（Conan 的 build 目录即源码副本，
  不污染仓库），需确认配方后续 `package()` 只安装产物而非中间文件；
- 本条目不改变编译结论，仅规范"相对 INCLUDES 失效时选 in-source 还是修 Makefile.am"。
