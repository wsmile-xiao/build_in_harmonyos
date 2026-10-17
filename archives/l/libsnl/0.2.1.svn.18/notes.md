# libSNL 0.2.1.svn.18 — HarmonyOS PC 适配说明

## 概况

libSNL（Simple Nurbs Library）是一个小型 C++ NURBS 库：NURBS 曲线/曲面、
控制点网、节点向量、变换、三角网格与线性方程组求解。

- 上游：http://libsnl.sourceforge.net/ （源码来源为 Debian orig tarball）
- 构建：**手写 `src/makefile`**（无 configure/CMake）
- 依赖：无（仅 C++ 标准库）
- 许可证：GPL-2.0-or-later

## 适配要点

| # | 问题 | 处理 |
|---|------|------|
| 1 | 无标准构建系统 | 按上游 `src/makefile` 的同一源码列表，直接用 OHOS clang++ 编译为 `libSNL.so.0.2`（并建 `libSNL.so` 软链；`shared=False` 时输出 `libSNL.a`），排除带 `main()` 的 `snlTest.cpp` |
| 2 | C++ 年代 | 2004 年代码，使用 `-std=gnu++98`（与上游一致，最稳） |
| 3 | 头文件包含方式 | 头文件之间是无限定 `#include "snlXxx.h"` → `src/*.h` 平铺安装到 `include/` |
| 4 | 上游测试程序 | `src/snlTest.cpp` 自带 `main()`：配方在 `build()` 中编译并真机执行，**要求输出包含 `All tests have passed :-)`**，否则构建失败（日志 `upstream-snltest.log`） |

## 测试

### 上游测试（build() 内执行，真机）

`snlTest` 覆盖：曲线/曲面全局插值、节点插入与移除、升阶、曲线追加、
曲面投影、三角网格细分等；全部通过时打印
`All tests have passed :-)`。

### 消费者测试（test_package，CMake）

`test_package/test_libsnl.cpp` 针对**安装后**的头文件/库，共 10 条断言：

- `snlPoint` 四个分量的存取
- `snlVector`：长度（3-4-5）、点积、叉积、两点距离
- `snlCurve`：`SNL_GLOBAL_INTERPOLATION` 生成的曲线过全部型值点（最大误差 ≤ 1e-9）、
  阶次/控制点数保持、参数区间递增

## 已知限制

- 上游 `snlTest` 的判定靠标准输出文本（其 `main` 恒返回 0），配方同时校验退出码与文本。
- 未修改上游任何源码或测试（`patches: []`）。
