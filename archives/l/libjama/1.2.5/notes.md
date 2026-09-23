# libjama 1.2.5 — HarmonyOS PC 适配说明

## 概述

JAMA/C++ 是 MathWorks/NIST 的公共领域 C++ 模板库，提供矩阵分解：

- `jama_lu.h`：LU 分解（`solve`/`det`/`isNonsingular`/`getL`/`getU`）
- `jama_qr.h`：QR 分解（`solve` 最小二乘/`getQ`/`getR`/`isFullRank`）
- `jama_cholesky.h`：对称正定矩阵 Cholesky 分解
- `jama_svd.h`：奇异值分解（`getSingularValues`/`norm2`/`cond`/`rank`）
- `jama_eig.h`：实矩阵特征值/特征向量（对称走 tred2/tql2）

矩阵存储类型（`Array1D`/`Array2D`）来自 TNT，由独立包 `libtnt` 提供。

- 上游：https://math.nist.gov/tnt/（源码取自 Debian orig tarball，public-domain）
- 形态：**纯头文件库**（`src/jama/*.h` 共 5 个）
- 依赖：`libtnt/1.2.6`（制品仓已发布）

## 适配要点

| # | 问题 | 处理 |
|---|------|------|
| 1 | 无构建系统 | `package_type="header-library"`，装 `include/jama/*.h`，`package_id()` 清空 |
| 2 | 非限定 `#include "tnt_*.h"` | 保持原样：已发布的 `libtnt/1.2.6` 把 TNT 头**平铺**在 `include/`，依赖传播后即可解析（**不要**照 Debian 改成 `<tnt/...>`，本仓 `libtnt` 没有 `tnt/` 子目录） |
| 3 | C++11 前代码：`using namespace TNT;` + `using namespace std;` + 未限定 `min/max` | 最小补丁把 `min/max` 限定为 `std::min/std::max`，`jama_eig.h`/`jama_svd.h` 去掉/注释头文件级 `using namespace std;`；`jama_cholesky.h` 的 `"math.h"` 改 `<math.h>` 并补上它缺失的 `#include "tnt.h"`（上游该头不自包含，依赖调用方先包含 TNT） |
| 4 | 上游无测试 | `build()` 编译包含全部公开头的 TU 作编译证据；`test_package` 做数值断言 |

## 测试

### 上游

上游仅 5 个头文件，无 `tests/`、无 `check` 目标、无 LICENSE。无测试可运行（技术原因：纯头文件模板库，上游未附带测试套件）。

### 消费者测试（test_package，CMake + ctest）

`test_package/test_jama.cpp` 共 **12** 条断言，逐项校验分解结果：

- LU：`[[4,3],[6,3]]·x=[10,12] → x=[1,2]`；`isNonsingular`；`det = -6`
- QR：`A=[1,1;1,2;1,3], b=[1,2,2]` 最小二乘 → `[2/3, 1/2]`；`isFullRank`
- Cholesky：`[[4,2],[2,3]]·x=[6,5] → [1,1]`；`is_spd`；`L=[[2,0],[1,√2]]`
- SVD：`diag(3,2)` 奇异值 `[3,2]`；`norm2=3`；`rank=2`
- 特征值：对称阵 `[[2,1],[1,2]]` → `{1,3}`
