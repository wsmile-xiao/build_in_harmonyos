# exprtk 0.0.3 适配笔记

## 编译环境
- 构建系统: header-only（无构建；上游测试经 CMake 工具链门控编译）
- 编译日期: 2026-09-19
- 编译器: clang/clang++ 15.0.4（aarch64 OHOS 原生）
- 状态: built（W3 conan-verify 通过）

## R02 返工（上游测试 23/23 全通过）

- 问题: R01 22/23（run_test21 FAILED）——上游测试断言 `z == (w += y / x)`（immutable 符号 w 的
  `+=` 复合赋值）应编译失败，但 0.0.3 解析器接受。
- 根因: exprtk.hpp `interval_container_t::add_interval` 用 `in_interval(end)` 判重叠，half-open
  策略把相邻 immutable 变量区间（如 w=[d8,e0)、z=[e0,e8)）的共享边界点误判为冲突，导致后登记
  区间被丢弃；嵌套表达式中 w 的区间未入 immutable map，检查落空，复合赋值静默成功。
- 修复: 新增 patches/0001-exprtk.hpp.patch —— add_interval 改真重叠检测
  （[begin,end) 与 [ebegin,eend) 仅当 begin<eend && ebegin<end 重叠，相邻区间合法），与 `:=`
  的 ERR268 行为一致。repro21b 复验：嵌套 case 现正确 ERR268。
- 验证: 全量 23/23 SUCCESS（upstream_full_run_r02.log sha256=5210c3e4…），run_test14 真实加载
  functional 数据 69.1s；run_test14 非交换子列表因官方仓库（全分支/全 tag/全历史）确无
  exprtk_noncommutative_test.txt 而为空，如实记录不写入真实通过（证据 run14_datafile_audit.log）。

## 编译步骤

1. W0 preflight：零依赖，直接通过。
2. lang-preflight：detected=cpp（exprtk.hpp 单头 + 26 个 cpp 示例/测试），通过。
3. conan-init 生成模板后按 header-only 检查清单重写：`package_type="header-library"`、`package_id()` clear、`generate()` 显式 CMakeToolchain、`package()` 只装 include/、无 libs（G3/G4/L2/L4/L5 全过）。
4. 上游测试门控选项 `run_upstream_tests`（默认 False，CI 与真机同一入口）：True 时生成最小 CMakeLists 到源码目录，CMake 工具链编译 exprtk_test.cpp（-O0）后直接运行。
5. 消费者测试 test.cpp：symbol_table/expression/parser 真实调用 API，6 项断言（表达式求值、变量重绑定重求值、min/max/pi 函数、非法表达式拒绝）。
6. 鸿蒙专项测试 harmonyos_specific_test.cpp：9 项断言（IEEE-754/libm 一致性、向量求和/均值、循环控制流与表达式重绑定），platform=OHOS(aarch64) 实测通过。
7. 真机全量验证：上游 23/23 结果由独立 clang++ 运行证实（见 test_ledger_r02.md / upstream_full_run_r02.log，data 文件置于 CWD）；conan build() 门控路径按同一命令集复现（-o run_upstream_tests=True）。

## 测试双口径账本

| 维度 | 数值 | 说明 |
|---|---|---|
| 上游静态声明总数 N_static | 23 | exprtk_test.cpp main() 顺序调用 perform_test(numeric_type,00..22)，展开为 run_test00..22，单一 double 类型（0.0.3 较 0.0.2 新增 run_test22） |
| 实际注册/可执行 N_registered | 23 | 全部纳入执行入口，无条件编译过滤 |
| 实际执行 N_executed | 23 | 真机全量执行 |
| 通过/失败/跳过 | 23 / 0 / 0 | R02 修复后全量通过（run_test21 由补丁修复） |
| 全量通过率 | 23/23 = 100% | 分母=全部独立上游用例 |
| 消费者测试 N_consumer | 1 | test_exprtk 程序，6 项断言，退出码 0 |
| 鸿蒙专项测试 | 1 | harmonyos_specific_test 程序，9 项断言，退出码 0 |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub urlopen 下载超时（init-build） | 本环境 python urlopen 直连 github.com 超时 | 用 git clone（git 协议可达）拉 tag 0.0.3，codeload.github.com 下载官方 tarball，sha256=f9dec697… 与 git 内容逐文件比对一致；init-build --no-download 复用 |
| 2 | run_test21 FAILED：`z == (w += y / x)` 期望编译失败(F) 实际编译成功 | 上游 0.0.3 `interval_container_t::add_interval` 用 `in_interval(end)` 判重叠，half-open 策略把相邻 immutable 变量区间共享边界点误判为冲突，后登记区间被丢弃，immutable 检查落空（`:=` 触发 ERR268 而嵌套 `+=` 未触发） | R02 补丁 patches/0001-exprtk.hpp.patch 改真重叠检测，与 `:=` ERR268 行为一致；repro21 复验 + 全量 23/23 |
| 3 | exprtk_noncommutative_test.txt 缺失 | 0.0.3 tarball 不含该文件（run_test14 引用） | load_expressions 空列表静默处理，不产生失败；如实记录 |
| 4 | E017 镜像注入残留 conandata.yml.ghfast-bak | conan-verify G2 临时注入 ghfast.top 镜像后恢复原文件 | 提交前删除 .ghfast-bak（JC1 拦截项） |

## 源码修改

补丁: patches/0001-exprtk.hpp.patch（add_interval 真重叠检测，纯逻辑修复无平台宏；conandata.yml 显式声明，build() 应用 apply_conandata_patches）。

## 依赖版本

无依赖（header-only 单头库）。

## 验证结果

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 -o 'exprtk/*:run_upstream_tests=True'
# 上游测试（真机全量，R02 修复后）：run_test00..run_test22 (double) 23/23 SUCCESS（含 run_test21）
# 消费者测试：exprtk consumer test: all checks passed
# 鸿蒙专项测试：harmonyos_specific_test: platform=OHOS(aarch64); all OHOS runtime checks passed
# conan create 完整成功（含 test_package 运行）
```

## 注意事项

- exprtk 0.0.3 上游 Makefile 使用 `-c++`（g++ 别名）与 `-Werror`，设备无 c++/cc 别名，故测试编译走 Conan CMake 工具链（clang++），不依赖 shell 编译器变量（R33）。
- 上游测试用 -O0 覆盖 release 优化仅加速编译，语义不变；全量 23 套件真机约 40 分钟，CI 默认选项跳过上游测试（消费者测试与鸿蒙专项测试仍全跑）。
- exprtk.hpp 装至 include/ 根，消费者 `#include "exprtk.hpp"` 与上游使用习惯一致。
- R02 修复记录：run_test21 根因（add_interval 相邻区间边界误判）已通过补丁修复并复验 23/23，见本文件 R02 小节与 patches/0001-exprtk.hpp.patch。
---

**编译结束**: 2026-09-19 15:44
**最终状态**: built
