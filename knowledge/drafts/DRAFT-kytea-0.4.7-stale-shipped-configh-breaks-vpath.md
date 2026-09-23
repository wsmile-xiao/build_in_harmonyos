# DRAFT-kytea-0.4.7-stale-shipped-configh-breaks-vpath — tarball 预生成 config.h 陈旧时 VPATH 构建 `#include <pkg/config.h>` 仍命中源码树旧文件，须 in-source 构建让 config.status 覆盖

> **Contributor**: kytea 0.4.7 适配 | **Status**: DRAFT（最终编号由知识库主编确认） | **Updated**: 2026-09-16
> **Severity**: blocking (2) | **Category**: autotools / VPATH / generated-header / conan-layout
> **Audience**: 在 OHOS 上适配"tarball 内随源码分发已生成的 config.h"的 autotools 项目的配方作者；与 E110/E434（因 HMDFS/ copystamp 必须 VPATH）方向相反的判据补充

## 触发（trigger）

- 上游 release tarball 内**携带维护者机器上生成的 `src/include/<pkg>/config.h`**（非 `config.h.in` 模板，是 configure 的产物被一并打包）。
- 该生成文件基于维护者环境，含有本机不成立的能力宏（kytea 0.4.7 实例：`HAVE_BOOST_TR1_UNORDERED_MAP_HPP`、`HAVE_TR1_UNORDERED_MAP` 等，系统无 boost/tr1 头）。
- 配方按常见实践（Conan `autotools_layout`、E110"用 VPATH 构建避开 HMDFS 源码树限制"）在独立 build 目录跑 configure。

## 症状（symptom）

VPATH 构建下 make 编译库源码即失败，首错形如：

```
kytea-0.4.7/src/include/kytea/config.h:63:11: fatal error:
    'boost/tr1/unordered_map.hpp' file not found
```

特征（判别要点）：

1. **错误路径在源码树**（`<srcdir>/src/include/kytea/config.h`），不是 build 目录；
2. `grep HAVE_BOOST <srcdir>/src/include/kytea/config.h` 有命中，而 builddir 下新生成的 `config.h`（裸名，位于 `-I$(top_builddir)/src/include/kytea`）是干净的；
3. 同一 tarball 在**源码树内**直接 `./configure && make` 却能编译通过——因为 config.status 以 AC_CONFIG_HEADERS 目标路径原地**覆盖**了陈旧文件；
4. 失败与编译器、sysroot、musl 无关（换 gcc/glibc 环境同样失败）。

## 机制（root cause）

上游 `configure.ac` 声明 `AC_CONFIG_HEADERS([src/include/kytea/config.h])`，且
`Makefile.am` 给库编译加 `-I$(top_builddir)/src/include/kytea`（让**裸名**
`#include <config.h>` 命中新生成文件）与 `-I$(top_srcdir)/src/include`。

源码里的包含形态是 `#include <kytea/config.h>`（带目录前缀）。解析时：

- VPATH 下 `-I$(top_srcdir)/src/include` 使 `<kytea/config.h>` 命中**源码树的陈旧文件**；
- `-I$(top_builddir)/src/include/kytea` 只能让 `<config.h>`（裸名）命中新文件——**它改变不了带 `kytea/` 前缀的查找**（除非 builddir 里真有 `<builddir>/src/include/kytea/kytea/config.h` 这一嵌套路径，而 AC_CONFIG_HEADERS 只生成 `<builddir>/src/include/kytea/config.h`）；
- 于是所有 `#include <kytea/config.h>` 的翻译单元读到维护者环境的能力宏集合，`#ifdef HAVE_BOOST_TR1_*` 分支被打开，拉入系统不存在的头，编译失败。

in-source（builddir==srcdir）时 config.status 直接覆盖源码树陈旧文件，问题不暴露——这也是"同一 tarball 有的构建方式过、有的不过"的机理。

## 方案（最小修复）

**配方级**：改用 in-source 构建，让 configure/config.status 原地覆盖陈旧头。

- Conan 2：`layout()` 用 `basic_layout(self)`（Conan 默认在 source_folder 内 configure），**不要** `autotools_layout`（它启用 build-folder 分离 = VPATH）；
- 手工构建：直接在解压目录 `./configure --prefix=<prefix>`。

对 kytea 0.4.7 实测：in-source 下 `grep -c 'define HAVE_BOOST' src/include/kytea/config.h` 由 1 变 0（陈旧宏被清除），编译/47 用例上游测试全过。

**替代方案**（配方想保留 VPATH 时，二选一）：

- 打源码补丁把 `AC_CONFIG_HEADERS` 输出路径改为 `$builddir` 下同名嵌套目录（如 `AC_CONFIG_HEADERS([src/include/kytea/kytea-config.h])` 并同步源码 include——改动面大，不推荐）；
- 或在 VPATH 构建前 `rm $(srcdir)/src/include/kytea/config.h` 并让 configure 重新生成（需确认 Makefile 对该文件的依赖不会触发 autoreconf）。

## 验证（kytea 0.4.7，2026-09-16 本机实测）

| 构建 | configure | 编译 | 归因 |
|------|-----------|------|------|
| VPATH（`mkdir build && cd build && ../configure`） | 通过 | **失败**：`boost/tr1/unordered_map.hpp not found`，错误路径指向 `<srcdir>/src/include/kytea/config.h` | `<kytea/config.h>` 命中源码树陈旧文件 |
| in-source（`./configure`） | 通过（config.status 覆盖陈旧 config.h） | **通过**；`make check` 1/1（test-kytea 6 套件 47/47） | 陈旧宏被清除 |

判别命令：

```bash
grep -n 'define HAVE_BOOST' <srcdir>/src/include/kytea/config.h   # VPATH 失败时非空；in-source 成功后为空
```

## 适用边界与反例

- **适用**：tarball 分发"已生成的带前缀路径 config.h"（`<pkg>/config.h` 形态，非根目录裸 `config.h`）且源码用 `#include <pkg/config.h>` 引用的 autotools 项目。根目录裸 `config.h` 场景 `-I$(top_builddir)` 即可让 VPATH 正确命中新文件，不受本条影响。
- **反例/反向**：E110（HMDFS 限制源码树临时文件创建，**须** VPATH）与 E434（in-tree cp 同文件失败，**须** VPATH）——这两类项目源码树不可写或不可 in-source，与本条"必须 in-source"方向相反。若项目同时踩中两类（源码树 HMDFS 只读 + tarball 陈旧头），本条的"替代方案"（VPATH + 删除陈旧头重生成）是唯一出路。
- 陈旧头的宏**无害**时（如只错一个 `PACKAGE_STRING`）不会触发本条；触发线是宏集合引入了本机不成立的能力分支（头文件缺失/链接失败）。
- HMDFS 上 in-source 构建的临时目录问题（E052/E011 umask）需另行处理，与本条正交。

## 关系

- similar_to: E110（VPATH 判据，方向相反）、E434（in-tree 失败须 VPATH，方向相反）
- conflicts_with: 无（判据层面互补：源码树可写 + tarball 带陈旧生成头 → in-source；HMDFS 只读 → VPATH + 删陈旧头）
- caused_by: 上游打包实践（`make dist` 把 `AC_CONFIG_HEADERS` 产物一并入包）
- 查重决定：`new_draft`——E110/E434 及全库检索无"tarball 预生成头 + VPATH include 前缀解析"条目；`boundary_novelty=yes`
