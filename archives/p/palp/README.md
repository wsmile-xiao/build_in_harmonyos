# palp

**PALP — a Package for Analyzing Lattice Polytopes**（格点多胞形分析工具集）

PALP 计算格点多胞形的顶点、格点、面、反射性，做 Newton 多面体与权重系统的分类，
是环面几何与 Calabi-Yau 流形研究里的标准工具。SageMath / passagemath 的
`sage.geometry.lattice_polytope` 直接调它的命令行程序。

## 用法

```bash
poly.x polytope.txt          # 顶点/格点/面的统计，如 "M:6 3 F:3"
poly.x -fv polytope.txt      # 打印顶点坐标
class.x -f                   # 反射多胞形分类/枚举
cws.x                        # 组合权重系统
nef.x                        # nef 部分与 Hodge 数
mori.x                       # Mori 锥与相交环
```

输入格式：首行 `<行数> <列数> [任意说明文字]`，随后逐行给出坐标（说明文字被忽略）。

## 维度后缀

同一程序按 `POLY_Dmax` 分别编译多份：

| 文件 | POLY_Dmax |
|---|---|
| `poly.x` `class.x` `cws.x` `nef.x` `mori.x` | 6（Global.h 默认值） |
| `*-4d.x` / `*-5d.x` / `*-6d.x` / `*-11d.x` | 4 / 5 / 6 / 11 |

维度是**编译期常量**，不是运行期参数——处理超过该维数的输入要换用对应后缀的程序。

## 构建

- 构建系统：纯 GNU Makefile（`GNUmakefile` 的 `all-dims` 目标），无 configure
- 许可证：GPL-2.0-or-later
- 源码：http://hep.itp.tuwien.ac.at/~kreuzer/CY/palp/palp-2.21.tar.gz

## 已编译版本

- 2.21 (2026-08-16)

## OHOS 适配

- CFLAGS 去掉 `-DNDEBUG`（源码 `assert()` 里有副作用表达式，预处理掉会改变语义）
- `package()` 逐个核对 25 个可执行文件，缺一即失败（防构建静默退化）
- `bin/` 下 ELF 全部 XPM 自签
