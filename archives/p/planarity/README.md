# planarity

**Edge Addition Planarity Suite** —— 图的平面性判定 / 平面嵌入 / Kuratowski 障碍子图隔离
与平面绘制的算法套件，来自 John M. Boyer（BSD-3-Clause）。

提供两部分产物：

- `libplanarity`：纯 C 图算法库（公共 API 由 `<planarity/graphLib.h>` 统一导出），
  实现边添加平面性算法、外平面性判定、K23/K33/K4 子图同胚搜索、平面绘制与图 I/O
  （邻接表 / 邻接矩阵 / g6）。
- `planarity`：命令行工具，可按算法处理单个图或批量回归测试。

## 用法

```bash
# 菜单模式（无参数）
planarity

# 帮助 / 版本 / 版权
planarity -h            # 等价 -help；也可用 --help
planarity --version
planarity -i            # 等价 -info

# 单图：平面性判定（返回 0=平面 / 1=非平面 / -1=错误）
planarity -s -q -p infile.txt embedding.out [obstruction.out]

# 单图：若可平面则画平面嵌入
planarity -s -q -d infile.txt embedding.out [drawing.out]

# 批量回归：对样本目录跑完整上游测试
planarity -test <samples dir>
```

库的使用（需 `-I<prefix>/include`）：

```c
#include <planarity/graphLib.h>

graphP g = gp_New();
gp_EnsureVertexCapacity(g, 4);
g->N = 4;                      /* 内存图 API 为 1-based，顶点 1..N */
gp_AddEdge(g, 1, 0, 2, 0);
...
int r = gp_Embed(g, EMBEDFLAGS_PLANAR);   /* OK / NONEMBEDDABLE / NOTOK */
gp_Free(&g);
```

> 注意：内存图 API 使用 **1-based** 顶点索引（`gp_GetVertexDegree(g, 1)`）；
> 邻接表**文件**为 0-based 文本。`gp_TestEmbedResultIntegrity()` 在成功路径上返回
> 与 `gp_Embed()` 相同的结果值。

## 构建

- 构建系统：autotools（发行包内已附带生成好的 `configure`，无需 autoreconf）
- 版本：5.0.0.0
- 许可证：BSD-3-Clause（见源码 `LICENSE.TXT`）
- 源码：https://github.com/graph-algorithms/edge-addition-planarity-suite/releases/download/Version_5.0.0.0/planarity-5.0.0.0.tar.gz
- 依赖：无（`configure.ac` 仅 `AC_PROG_CC` / `AC_PROG_INSTALL` / `AC_CHECK_HEADERS`，全为 libc 头文件）
- 安装产物：`bin/planarity`、`lib/libplanarity.a`（或 `shared=True` 时的 `libplanarity.so`）、
  `include/planarity/**`、`lib/pkgconfig/libplanarity.pc`、`share/doc/planarity/samples/`、
  `share/man/man1/planarity.1`
- 消费者用法：CMake `find_package(planarity)` → `planarity::planarity`；
  pkg-config 名 `libplanarity`

## OHOS 适配（4 个补丁，见 `5.0.0.0/patches/`）

| 补丁 | 内容 |
|---|---|
| `0001-c-planarityApp-planarityCommandLine.c.patch` | CLI 增加 GNU 长选项 `--help`（等价 `-h`）与 `--version`（单行 `planarity <ver>`）；上游只认单横线 `-h`/`-help`，标准 CLI 探测（Conan L2 冒烟门禁）会失败 |
| `0002-config.guess.patch` | `config.guess` 增加 `HarmonyOS` 系统识别分支 → 输出 `aarch64-unknown-linux-ohos`（否则 `configure: error: cannot guess build type`） |
| `0003-config.sub.patch` | `config.sub` 接受 `linux-ohos` 三元组 |
| `0004-configure.patch` | `configure` 内两处 `umask 077` 改为 `umask 022`：HMDFS 给新目录强制 setgid 且属主映射为共享属主，`drwx--S---` 目录连创建者都不可写，`config.status` 的临时目录会创建失败 |

补丁新增行不含平台宏（`__OHOS__`），走 POSIX 兼容写法。

## 测试

- 上游：`make check`（`Makefile.am` 的 `TESTS = test-samples.sh`）→ `# TOTAL: 1 / # PASS: 1`；
  该测试程序内部驱动 40 项比对（1-based / 0-based 嵌入与障碍隔离、g6 / 邻接表 / 邻接矩阵
  图变换输出比对、`n8.mALL.g6` 全图批量）。
- 消费者（`5.0.0.0/test_package/`）：库 API 42 条断言 + CLI 7 条断言，均在
  `conan create` 的 `test_package` 阶段实际执行。
