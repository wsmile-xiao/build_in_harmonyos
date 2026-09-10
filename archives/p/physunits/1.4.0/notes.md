# physunits 1.4.0 适配笔记

## 基本信息
- **上游**: https://github.com/martinmoene/PhysUnits-CT-Cpp11
- **版本**: 1.4.0（上游 tag v1.4.0，2026-02-14 发布）
- **许可证**: BSL-1.0
- **类型**: header-only C++11 库（CMake INTERFACE library，40 个头文件 `phys/units/*.hpp`）

## 依赖
无第三方依赖：全部头文件仅 `#include` C++ 标准库（algorithm/cmath/limits/utility/string/stdexcept 等）。

## 构建系统
CMake ≥ 3.15，INTERFACE 目标 `PhysUnits` / `PhysUnits::PhysUnits`。
- `PHYS_UNITS_OPT_BUILD_TESTS=ON` 启用上游测试（lest 框架内置于 `test/lest/lest_cpp03.hpp`）
- clang 15 下 CTest 运行 4 个测试: test-cpp11/test-cpp14/test-cpp17/test-cpp20
- 每个可执行文件运行同一 30 个 lest 用例（456 条 passed expectation，0 failed / 0 skipped）

## 编译步骤
1. `ohc-run.py init-build physunits 1.4.0 --url=<官方 tarball>`：源码 .orig/.work + 归档骨架
2. `ohc-run.py lang-preflight`：detected=cpp（CMake manifest，cpp 98%）
3. conan-init 生成的是 autotools 模板 → 手工重写为 header-only CMake 配方
   （conanfile.py + conandata.yml sha256 + test_package 真实消费者测试）
4. 上游独立构建/测试（clang 15, OHOS aarch64 本机）：
   `cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DPHYS_UNITS_OPT_BUILD_TESTS=ON`
   → `cmake --build build -j4` → `ctest --output-on-failure`（4/4 通过）
5. `conan create archives/p/physunits/1.4.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=...`
   → 主包（上游 ctest 4/4）+ test_package（消费者测试运行通过）
6. `ohc-run.py conan-verify physunits 1.4.0` → G0/G1/G2/G3/G4 + L2/L4/L5 全 PASS
7. `ohc-run.py finish physunits 1.4.0 built`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-init 生成 autotools 模板 | 模板默认 autotools，与 header-only CMake 工程不符 | 手工重写 header-only CMake 配方（参考 optional-lite 3.5.0 归档） |
| 2 | conan-verify G1 失败 | G1 字面检查要求 conanfile.py 含 `export_sources`/`apply_conandata_patches` | 补 export_sources() + source() 中 apply_conandata_patches()（patches 为空，无副作用） |
| 3 | test_package 编译错：`Quotient<...> 无成员 magnitude()` | 库默认 `PHYS_UNITS_COLLAPSE_TO_REP=1`，无量纲 `.to(unit)` 结果折叠为 double | 测试改为 `fabs(hours - 1.0)`（去掉 .magnitude()） |
| 4 | finish Step3 G0 clean-verify exit 127 | G0 仅按 autotools 执行 `./configure`，CMake header-only 无 configure | SKILL 定义 G0 非阻塞；真实构建验证以 conan-verify G2 + W3 本地 CI 为准 |

## 依赖版本
- 编译工具链: clang/clang++ 15（OHOS SDK，conan profile `ci/conan/profiles/ohos-aarch64`）
- cmake 4.1.2
- 无第三方库依赖

## 验证结果
```bash
# 上游独立构建 + 测试（本机 OHOS aarch64）
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DPHYS_UNITS_OPT_BUILD_TESTS=ON   # exit=0
cmake --build build -j4                                                            # exit=0
ctest --output-on-failure                                                          # 4/4 Passed

# conan 干净构建 + 消费者测试
conan create archives/p/physunits/1.4.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64  # exit=0

# 验证门禁
ohc-run.py conan-verify physunits 1.4.0   # exit=0, G0-G4+L2/L4/L5 PASS
```

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | header-only CMake 配方（package_type=header-library） |
| conandata.yml | 官方源 + sha256 |
| test_package/ | 消费者测试（test_physunits.cpp，C++11） |
| reports/test-report.md | 上游测试报告 |

## 注意事项
- 头文件安装到 `include/phys/units/`；CMake target `PhysUnits::PhysUnits`
- G0 clean-verify 对 CMake 纯头文件包不适用（仅 autotools），以 G2/W3 为准

## 对话记录

### 对话 #1
- 问：conan-init 为 physunits 生成的 autotools 模板正确吗？
- 答：不正确。physunits 是 header-only CMake INTERFACE 工程，需重写为 header-only
  CMake 配方（package_type=header-library；cpp_info 映射 PhysUnits::PhysUnits）。
- 经验：conan-verify G1 字面要求 conanfile.py 含 export_sources/apply_conandata_patches；
  空 patches 也要保留调用。

### 对话 #2
- 问：test_package 里 `(3600.0_s).to(hour).magnitude()` 编译失败，为什么？
- 答：physunits 默认 `PHYS_UNITS_COLLAPSE_TO_REP=1`，无量纲结果（同量纲之比）折叠为
  double，不再具备 .magnitude()。消费者测试需直接比较折叠值。
- 经验：finish Step3 G0 clean-verify 仅支持 autotools（./configure）；CMake 纯头文件包
  会 exit 127，属 SKILL 定义的非阻塞步骤，最终以 conan-verify G2 + W3 本地 CI 为准。
---

**编译结束**: 2026-09-03 17:16
**最终状态**: built
---

**编译结束**: 2026-09-03 17:23
**最终状态**: built
