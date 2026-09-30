# DRAFT-nnom-0.4.3-self-typedef-fixed-point-dual-dir-headers — 无 CMSIS 依赖的自给定点类型 + 双目录头文件安装

> 草稿编号：DRAFT-nnom-0.4.3-self-typedef-fixed-point-dual-dir-headers（同 stem .kv 配对）
> 来源库：nnom 0.4.3（majianjia/nnom，microcontroller neural-network library）
> 作者：AtomCode | 日期：2026-09-29 | 路径判定：new_draft（P 路径 B）

## 问题

嵌入式神经网络/定点库（如 nnom）在 HarmonyOS PC (aarch64, musl) 上适配时：
1. 库自带 `q7_t/q15_t/q31_t/q63_t` 等定点类型（由 `inc/nnom.h` 直接 typedef 为
   `int8_t/int16_t/int32_t/int64_t`），并不真正依赖 ARM CMSIS 头文件——但部分
   源文件含 `#include "arm_math.h"`，若不做判断就按 CMSIS 依赖处理，会误拉入
   CMSIS 依赖或误判裁剪。
2. 头文件以双目录布局发布：`inc/*.h` 平铺 + `inc/layers/*.h` 子目录 +
   `port/nnom_port.h` 根部；消费方 `#include "layers/nnom_conv2d.h"`（子目录相对
   路径）与 `#include "nnom_port.h"`（根部）。Conan package() 若只做单目录平铺
   复制，消费编译立刻失败（`layers/nnom_*.h` 找不到）。

## 根因

- `q7_t` 等类型由库自身 typedef（`inc/nnom.h` 第 31-34 行），`arm_math.h` 仅被
  `NNOM_USING_CMSIS_NN` 宏守卫、默认不编译。适配者若不读源码就会以为需要 CMSIS
  toolchain 依赖（R11 "先查归档再动手"）。
- 头文件组织是「根头 + 子目录层头 + 独立 port 头」三形态混合，`nnom_layers.h`
  以 `#include "layers/nnom_xxx.h"` 相对引用、`nnom.h` 以 `#include "nnom_port.h"`
  根引用；Conan 安装头文件必须**保结构**（子目录保留、port 头并入根）。

## 方案

1. **判定定点类型来源**：grep `typedef.*q7_t|arm_math.h|NNOM_USING_CMSIS_NN`；
   若类型自 typedef 且 CMSIS 头被宏守卫 → 不引入 CMSIS 依赖，按普通 C 库编译。
2. **双目录头文件安装**（Conan `package()`）：
   - `inc/*.h` → `include/`（平铺，keep_path=False）
   - `inc/layers/*.h` → `include/layers/`（保留子目录，keep_path=False 且显式 dst）
   - `port/nnom_port.h` → `include/`（根并入，因为 `nnom.h` 按根引用）
3. **libm 补充**：激活函数用 `tanh/round` 等，`self.cpp_info.system_libs = ["m"]`。
4. **静态库**：`cc -c -O2 -fPIC -std=c99 -I inc -I port` 直接编译全部核心/层/后端
   源文件 + `llvm-ar rcs libnnom.a`（R33：编译器取自 Conan conf）。
5. **消费者验证**：test_package 通过公开 API（Input/Dense/Output + model_compile/
   model_run）构建模型并断言量化前向输出（含负输入符号路径），证明安装后头文件
   布局与链接均可用。

## 验证

- conan create（-pr:h=ci/conan/profiles/ohos-aarch64，clang 15 / armv8）：通过
- test_package：test_nnom（10*2+0=20）+ test_ohos（±输入符号路径、NNOM_VERSION==403）2/2 通过
- 头文件消费编译：`find_package(nnom)` + `target_link_libraries(... nnom::nnom)` 成功
- 定点类型自给定性：`grep -c 'arm_math.h' src/` 实测 11 处包含，全部被 NNOM_USING_CMSIS_NN 守卫，
  无 CMSIS 依赖注入

## 适用边界 / 反例

- 适用：自带 q7/q15/q31 风格定点 typedef 且头文件含子目录结构的嵌入式 NN/定点 C 库；
  任一“根头 + 子目录层头 + 独立 port 头”三元结构库。
- 反例：真正依赖 ARM CMSIS-NN 优化后端的库（须按 NNOM_USING_CMSIS_NN 注入）——
  本模式不适用于启用 CMSIS-NN 的构建；header-only 无编译库走 E257。

## 查重差异（四范围）

| 既有条目 | 差异 |
|---|---|
| E257 header-only no-op build | 本模式为需编译的静态库，且头文件为双目录保结构安装 |
| E307 profile-compiler-direct-compile | 同 conf 直编思路，但 E307 面向 test_package compile-only；本条目含双目录头安装与定点类型自给判定 |
| E501 direct-compile-source-list-and-wrap-link-env | 同 Makefile 直编，但目标为 raw-Makefile 库；本条目为无构建系统 + 自给定点类型 + 双目录头 |
| DRAFT-arduinospritzcipher-1.2.0-no-build-family-manual-compile | 同无构建族手动编译核心模式（已复用），但其头文件为单头平铺；本条目新增「子目录层头 + port 头根部保结构安装」与「定点类型自给→免 CMSIS」两个可跨库复用差异 |

## 七轴查重结论

`exact_duplicate=false, causal_duplicate=false, trigger_overlap=false,
solution_overlap=partial, combination_novelty=true, boundary_novelty=true,
test_migration_novelty=false` → **new_draft**
relations: similar_to=[E257, E307, E501, DRAFT-arduinospritzcipher-1.2.0-no-build-family-manual-compile]; caused_by=[]; prerequisite_of=[]; conflicts_with=[]

## 证据（Evidence）

- 配方：`archives/n/nnom/0.4.3/conanfile.py`（package() 双目录安装 + system_libs m）
- 测试：`archives/n/nnom/0.4.3/test_package/test_nnom.c`、`test_ohos.c`
- 日志：`archives/n/nnom/0.4.3/reports/conan-verify-report.md`、`w3-local-ci.log`