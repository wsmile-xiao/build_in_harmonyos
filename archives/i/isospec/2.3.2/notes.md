# notes.md — isospec 2.3.2 适配记录

## 编译环境

- 构建系统: cmake（上游 CMake ≥3.12，C++17）
- 编译日期: 2026-09-21
- 编译器: clang/clang++ 15.0.4（`/data/service/hnp/bin/`）
- 状态: built

## 编译步骤

```bash
# 探索阶段（模板 B Step 2）
cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX
cmake --build . --target IsoSpec++-shared IsoSpec++-static -- -j4
```

配方化后（conan create，-j4）：configure + 只构建两个库目标；`package()` 自行拷贝
头文件与库（**不跑全局 install**，原因见问题 #1）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 全局 `cmake --install` 会失败 | 根 CMake `add_subdirectory(man)`，man 的 install 规则引用 doxygen/rsvg 产物（纯库构建下不存在） | 配方只构建两个库目标，package() 拷贝 headers+libs，零补丁 |
| 2 | OHOS 产物无 SONAME/符号链 | CMake 的 Platform/HarmonyOS 模块未实现 soname 链（configure 有 "post your config file" 提示） | 如实记录：单实体 `libIsoSpec++.so`，按名链接/解析自洽可用 |
| 3 | 设备 dlopen 拒载 NDK 本机构建 .so | 内容级拒载边界（文件名/目录/依赖/16K 对齐逐因子排除） | 配方加 `-Wl,-z,max-page-size=16384`；绑定层测试 NOT_RUN；知识草稿 E653 |
| 4 | tests/C/*.c 编译失败 | 上游相对 include 假定旧版根级布局（2.3.2 已移至 src/） | 按上游 Makefile 假定布局补 symlink 后正常编译运行（仅测试侧，不改源码） |
| 5 | lang-preflight 判 python | 根级 pyproject.toml（scikit-build PyPI 元数据）误判为主体 | 按 R47 边界规则确认主体为 C++（根 CMake 直建 src/IsoSpec++/），继续适配并留痕 feedback |

## 源码修改

无补丁（patches_applied: []）。上游测试失修项（test_arrays.c）与布局差异只在
**测试运行环境**处理，不改上游源码。

## 依赖版本

无第三方依赖。boost 二项分布采样器以 `src/IsoSpec++/btrd.h` vendored（Boost 软件
许可 1.0，文件头自述「avoid dependency on the whole Boost」）。

## 上游测试清点与实测

| 口径 | 数 | 依据 |
|---|---|---|
| 上游 CI 注册（pytest，唯一 CI 口径） | 301 | run_tests.yml：1 + 25×11 + 2 + 13 + 10 |
| C++ 主测试执行单元（TEST 宏调用） | 1276 完整 / 1144 SKIP_SLOW | main_test.cpp：formulas × 11 probs × 4 functions |
| C 测试程序 | 3 | tests/C/Makefile |
| test_package 消费者断言 | 11（4+7） | test_isospec.cpp + test_ohos.cpp |

实测（沙箱 HOME，clang 15.0.4）：

- main_test 快速变体 **1144/1144 通过**（rc=0）；完整变体 **1276/1276 通过**（rc=0）
- C wrapper：test_IsoThresholdGenerator rc=0、test_IsoOrderedGenerator rc=0
- test_arrays.c **NOT_RUN**（上游失修：引用 2.3.2 已删除的
  MassSpectrum/set_tablesIsoOrderedGenerator + 缺分号，证据见 reports）
- pytest 301 **NOT_RUN**（dlopen 拒载，E653）

## 验证结果

```bash
# conan create（static 默认）rc=0：test_isospec 4/4 CHECK + test_isospec_ohos 全过
# conan create -o "isospec/*:shared=True" rc=0：loader dlsym 断言真跑通过
H2O1 @ threshold 0.01: 1 configurations
C1H1O2N2Se1Sn1P1 @ 0.999: 179 confs, prob sum 0.99900597
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libIsoSpec++.a 或 lib/libIsoSpec++.so | 库本体（options.shared 分支），OHOS shared 为 16K 对齐 |
| include/IsoSpec++/*.h,*.hpp | 全部公开头（18 项，含 cwrapper.h C API） |

## 注意事项

- lang-preflight 误判 python 的完整证据链与工具缺陷记录见
  `feedback/pending/2026-09-21-isospec-2.3.2.md`；误判终态落在共享单槽位
  `$HOME/ohpcd-ai-worker-result.json`（无任务消费方，不作结论）。
- 消费 C++ API：`#include <IsoSpec++/isoSpec++.h>`；C API：`#include <IsoSpec++/cwrapper.h>`。
- 上游 tests/Python 依赖 `OldIsoSpecPy`（PyPI 旧版对拍包）+ cffi，设备不可用
  （E653）；tests/cppyy 需 cppyy，同样不可用。
---

**编译结束**: 2026-09-22 00:32
**最终状态**: built
