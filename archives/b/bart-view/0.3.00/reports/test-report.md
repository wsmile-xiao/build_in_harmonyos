# 测试报告 — bart-view 0.3.00（HarmonyOS PC / OHOS aarch64）

> **项目**: bart-view (mrirecon/view)
> **测试日期**: 2026-10-10
> **测试环境**: HarmonyOS HongMeng Kernel 1.11.0 aarch64（clang 15.0.4 / musl libc）
> **测试类型**: 上游构建入口复跑 + 新增鸿蒙特有功能测试（输出内容真值比对）+ conan create/verify

---

## 一、测试摘要

### 1.1 上游测试入口

上游**没有自动化测试**：全仓 15 个文件、无 `tests/` 目录，Makefile 只有
`all`/`view`/`cfl2png`/`install`/`clean` 目标（`grep -nE 'test|check' Makefile`
无匹配），`.gitlab-ci.yml` 只跑 `make all`。

| 指标 | 数值 | 说明 |
|:----:|:----:|:-----|
| 上游用例总数 | 0 | 无测试框架/用例 |
| 上游构建入口 | `make all` | recipe build() 实际执行 |
| 构建入口结果 | PASS | 产出 `view`、`cfl2png` |

### 1.2 适配后测试（新增鸿蒙特有测试）

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 命名检查 | 23 | 100% |
| 逐像素真值比较 | 1283 | 100% |
| 通过 | 1306 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**核心功能通过率**: ✅ **100%**（`conan create` 中 test_package 自动执行）

---

## 二、测试结论

### 2.1 总体评价

✅ **通过**。测试不是"文件存在/大小合理"式弱断言，而是**验证输出内容**：

- 测试自带 PNG 解码器（chunk 解析 + CRC 校验 + zlib 解压 + 反滤波），读出
  `cfl2png` 实际写出的像素；
- 与**独立推算的真值**逐点比对。真值依据上游算法：MAGN 灰度为
  `trunc(255 * clamp((scale*|v| - winlow)/(winhigh - winlow), 0, 1))`，
  `scale = 1/max`（相对窗口）或 `1`（`-A` 绝对窗口）；
- 构造的数据集使该式在浮点下逐位精确（值取 `n/256`、`n/255`），故可做**零容差**比对。

### 2.2 可用功能清单

```
✅ cfl2png 绝对窗口 (-A)      : 256 像素零容差真值比对（含 x/y 方向）
✅ cfl2png 相对窗口 (默认)     : 自动求 max，|像素-真值|<=1 且单调，端点 0/255
✅ cfl2png 翻转 (-FZ)         : 零容差 out(x,y)=src(15-x,15-y)
✅ cfl2png 色图 (-CV viridis) : 端点色与参考一致
✅ cfl2png 缩放 (-z)          : 默认 32x32、-z1 16x16
✅ cfl2png 边界 (全零数据)     : max==0 -> max=1 分支，输出全黑不透明
✅ cfl2png CLI 校验            : 非法窗口被拒（134/SIGABRT）
✅ view (GTK3)                : 依赖栈完整加载（无头环境停在 display open）
```

### 2.3 已知限制

1. `view` 是交互式 GTK3 GUI，本环境无图形显示，**窗口/渲染路径需人工确认
   （R40）**；仅验证依赖栈加载到 display open；
2. 上游无测试，无法给出"上游用例通过率"——只能复跑其构建入口 `make all`。

---

## 三、测试详情

### 3.1 执行的命令

```bash
# 1. 上游构建入口（recipe build() 内实际执行的 make 默认目标 = make all）
make -j1 SHELL=/bin/sh CC=<clang> BART_TOOLBOX_PATH=<vendored bart> ... view cfl2png

# 2. conan create（含 test_package 自动测试）
conan create archives/b/bart-view/0.3.00 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 -r=ohpcd

# 3. test_package 单独复跑（便于查看逐项输出）
python3 test_package/test_cfl2png.py <package_bin_dir>
```

日志路径：

- conan create: `archives/b/bart-view/0.3.00/reports/conan-create.log`
- conan-verify: `archives/b/bart-view/0.3.00/reports/conan-verify-report.md`
- 本地 CI 模拟（W3）: `archives/b/bart-view/0.3.00/reports/w3-local-ci.log`

### 3.2 通过的测试（鸿蒙特有测试 test_cfl2png.py，23 项检查 + 1283 像素比较）

| # | 测试项 | 验证内容 | 结果 |
|:-:|--------|----------|:----:|
| 1 | cfl2png executable | 包产物 bin/cfl2png 可执行 | ✅ PASS |
| 2 | view executable | 包产物 bin/view 可执行 | ✅ PASS |
| 3 | absolute-windowing conversion exits 0 | `-A -z 1` 转换退出码 0 | ✅ PASS |
| 4 | png header is 8-bit RGBA, non-interlaced, 16x16 | IHDR：depth=8/color=6/无隔行/尺寸 | ✅ PASS |
| 5 | png contains IHDR/IDAT/IEND chunks | chunk 结构与 CRC 校验通过 | ✅ PASS |
| 6 | all 256 pixels match computed gray exactly | 真值 `trunc(255n/256)` **零容差**（256 像素） | ✅ PASS |
| 7 | relative-windowing conversion exits 0 | 默认相对窗口转换退出码 0 | ✅ PASS |
| 8 | auto-windowing gray within 1 level of n | 自动求 max 正确（256 像素，max diff<=1） | ✅ PASS |
| 9 | auto-windowing monotonic and spans 0..255 | 灰度单调非减、端点 0/255 | ✅ PASS |
| 10 | auto-windowing is opaque RGB gray | R=G=B、A=255（256 像素） | ✅ PASS |
| 11 | flip (XY) conversion exits 0 | `-FZ` 转换退出码 0 | ✅ PASS |
| 12 | flip XY maps out(x,y)=src(15-x,15-y) exactly | 翻转映射**零容差**（256 像素） | ✅ PASS |
| 13 | viridis colormap conversion exits 0 | `-CV` 转换退出码 0 | ✅ PASS |
| 14 | viridis low end is the viridis start colour | `(68,1,84,255)` 精确 | ✅ PASS |
| 15 | viridis high end matches reference +-4 | `(250,230,34,255)`±4 | ✅ PASS |
| 16 | viridis mid tone is a colour | 中间调通道互异 | ✅ PASS |
| 17 | all-zero dataset conversion exits 0 | 全零数据转换退出码 0 | ✅ PASS |
| 18 | all-zero data renders fully black and opaque | 全黑不透明（256 像素） | ✅ PASS |
| 19 | default zoom 2 produces 32x32 | 缩放尺寸正确 | ✅ PASS |
| 20 | repeated conversion is byte-identical | 确定性 | ✅ PASS |
| 21 | invalid window is rejected (non-zero exit) | CLI 校验（实测 134） | ✅ PASS |
| 22 | view loads without missing shared library | GTK3 依赖栈完整 | ✅ PASS |
| 23 | view GTK3 init reaches display open | 到达 display open（无头环境预期） | ✅ PASS |

被测断言总数：**23 项命名检查 + 1283 次逐像素真值比较**，全部通过。

### 3.3 失败的测试

无。

### 3.4 跳过的测试

无（不适用上游测试套件，因为上游无测试）。

---

## 四、关键问题分析

### 问题 1: `ld.lld: error: undefined symbol: UNUSED`

**现象**：
```
ld.lld: error: undefined symbol: UNUSED
clang-15: error: linker command failed with exit code 1
```

**根因**：`view.c`/`draw.c` 使用 `UNUSED(x)` 宏，该宏由 BART `misc/misc.h`
提供；BART v1.0.00 删除了它（v0.9.00 及以前存在）。

**解决方案**：vendored BART 构建期在 `src/misc/misc.h` 恢复
`#define UNUSED(x) (void)(x)`。

### 问题 2: `src/cfl2png.c:133: error: incompatible integer to pointer conversion`（`rindex`）

**现象**：
```
src/cfl2png.c:133:14: warning: call to undeclared function 'rindex'; ...
src/cfl2png.c:133:8: error: incompatible integer to pointer conversion initializing 'char *' with an expression of type 'int'
```

**根因**：`rindex()` 是 BSD 遗留接口，musl 的 `strings.h` 不声明它；clang 15
把隐式声明视为返回 `int`，触发 `-Wint-conversion` 错误。

**解决方案**：改为标准等价 `strrchr()`（`#include <string.h>` 已存在）。

### 问题 3: clang 15 对 BART 源码的严格性报错

**现象**：`label at end of compound statement`、`case` 后带初始化器声明、
`[[fallthrough]]`（gnu17）等编译错误。

**根因**：GCC 宽松接受，clang 15 严格。

**解决方案**：随 `bart/1.0.00` recipe 的同一组精确文本补块/替换处理。

---

## 五、测试环境

```
软件版本:   bart-view 0.3.00 (mrirecon/view v0.3.00)
构建系统:   裸 Makefile（make all → view + cfl2png）
编译器:     clang 15.0.4 (OHOS SDK, aarch64-linux-ohos, musl libc)
依赖:       gtk/3.24.43  libpng/1.6.58  fftw3f/3.3.9  openblas/0.3.33
           + vendored BART v1.0.00 (libmisc/libgeom/libnum 静态链接)
```

---

*报告生成时间: 2026-10-10*
