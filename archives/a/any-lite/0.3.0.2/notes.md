# any-lite 0.3.0.2 适配笔记

## 基本信息
- **上游**: https://github.com/martinmoene/any-lite （GitHub 301 跳转到 nonstd-lite/any-lite 组织）
- **版本**: 0.3.0.2（上游正式标签 `v0.3.0` → commit `8f7c53c605cc51d067a16c06054a7a4c23945a10`，Release 2020-11-28）
- **任务分支**: feat/any-lite-0.3.0.2
- **许可证**: BSL-1.0 (Boost Software License)
- **类型**: header-only C++ 库 (CMake INTERFACE library)
- **前置版本**: 本仓库已有 0.3.0 bootstrap 草稿与 0.3.0.1 归档；本版本补齐完整适配与真机实测
- **上游自带 Conan 1.x 配方**（`from conans import ...`）；本归档按 Conan 2.x 重写（optional-lite 同款模式）

## 修订记录（0.3.0.2 相对 0.3.0 草稿版适配）

- **版本号递增（L0j/R37）**: 制品仓已发布 `any-lite/0.3.0`（bootstrap 草稿配方）与 `any-lite/0.3.0.1`（8-31 归档），
  cnb.cool 制品仓不支持同版本多 revision 并存；本归档重写了 conanfile.py/conandata.yml，
  与仓内已有 recipe 均不同，按 CI 提示「适配修复必须递增版本号后缀」取 0.3.0.2
- **分支名去 v（L0n/R40）**: 门禁要求分支名以不含 v 的 `包名-版本号` 结尾；
  原分支 `feat/any-lite-v0.3.0` 触发 R40 拦截，改为 `feat/any-lite-0.3.0.2`
- **提交真机验证报告**: `reports/conan-verify-report.md` 与 `reports/conan-create.log` 随归档提交

## 依赖
无任何依赖，仅包含单个头文件 `include/nonstd/any.hpp`（C++17 下默认别名到 `std::any`）。

## 构建系统
CMake，header-only INTERFACE library。
- `ANY_LITE_OPT_BUILD_TESTS=ON` 启用上游测试，`ANY_LITE_OPT_BUILD_EXAMPLES=OFF` 关闭示例
- 上游测试使用 lest 框架，**内置于 tarball**：`test/lest_cpp03.hpp`（由 `test/any-main.t.hpp` 直接 include，非子模块），无需网络
- clang 下 CTest 构建 4 个变体: cpp98/cpp11/cpp14/cpp17（目标名 `any-lite-cppXX.t`）

## 安装产物
- 头文件: `include/nonstd/any.hpp`
- 许可证: `licenses/LICENSE.txt`（上游 CMake install 不安装 LICENSE.txt，配方显式 copy）
- CMake 包配置: `any-lite-config.cmake` / `any-lite-targets.cmake`，目标 `nonstd::any-lite`

## 上游测试统计（四类数字口径）

1. **上游源码静态声明总数: 46 个 lest CASE**
   - `test/any.t.cpp`: 40 个功能用例（逐个 `grep -c 'CASE('` 统计：构造/赋值/emplace/swap/any_cast/bad_any_cast/tweak header）
   - `test/any-main.t.cpp`: 6 个诊断用例（版本/配置/`__cplusplus`/编译器版本/C++ 语言与库特性报告）
   - 交叉验证: `any-lite-cpp17.t --list-tests '*'` 输出 46 行，与静态统计一致
2. **官方套件实际执行数: 4 变体 × 40 用例 = 160 次用例执行，全部通过**
   - ctest 汇总: `100% tests passed, 0 tests failed out of 4`（test-cpp98/cpp11/cpp14/cpp17）
   - 每个变体 lest 输出 `All 40 selected tests passed.`
3. **未执行/跳过数: 每变体 6 个用例（4 变体共 24 次未执行）**
   - 全部为 `test/any-main.t.cpp` 中带 `[.tag]` 隐藏标签的诊断用例（lest 默认不选中，上游有意设计，非 OHOS 平台原因）
   - 40 个功能用例的 `CASE(...)` 注册无条件编译于全部 4 个变体（C++11-only 断言体内部用
     `#if any_CPP11_OR_GREATER` / `#if any_USES_STD_ANY` 条件编译），因此四变体注册列表一致
4. **新增 test_package 消费者测试: 2 个程序 10 个断言，全部通过**
   - `test_any_lite.cpp`（C++17，默认 `std::any` 模式）: 4 个断言——int/string 的 `any_cast`、
     默认构造空 any、赋值后 `has_value()`
   - `test_any_lite_cpp11.cpp`（C++11，nonstd 回移实现模式）: 6 个断言——`any_cast` 值/指针、
     `type()`、`has_value()`、`bad_any_cast` 异常路径

## 补丁说明（1 个，portability）
- `patches/0001-cpp98-algorithm-swap.patch`：上游 `any.hpp` 仅在 C++17 分支
  `#include <utility>`，cpp98 模式下 `any::swap()` 的 `std::swap` 依赖传递包含。
  旧工具链（g++ 4.8/5.x，上游 2020 年 CI）靠 `<type_traits>` 传递包含侥幸编译通过，
  新工具链（g++ 13 / clang 15）上 cpp98 变体编译失败：`'swap' is not a member of 'std'`。
  C++98 中 `std::swap` 声明于 `<algorithm>`，补丁在非 C++17 分支补该头文件，
  未改动任何测试用例与库语义。
- 本地桌面交叉验证（g++ -std=c++98/11/14/17）: 打补丁前 cpp98 编译失败，
  打补丁后 4 个变体全部编译通过，各变体均输出 `All 40 selected tests passed.`

## OHOS 适配
- E092: CMake 不识别 OHOS。配方 generate() 中设置 `CMAKE_SYSTEM_NAME=Linux` +
  `CMAKE_SYSTEM_PROCESSOR=<settings.arch>`（R32: `settings.os in ("Linux", "OHOS")` 判断）
- `CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY` 避免 header-only 项目的编译器探测链接步骤
- 除上述 1 个 portability 补丁外源码无需其他改动
- 本机（aarch64 鸿蒙）conan create 时 can_run 为真，上游测试与消费者测试均真实执行

## 验证命令
```bash
export CONAN_HOME="$HOME/tmp/ch/home-any-lite"
export SSL_CERT_FILE="$HOME/usr/local/ssl/cert.pem"
python3 scripts/ohc-run.py conan-verify any-lite 0.3.0.2
# conan create: -pr:h/-pr:b ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
```
- conan-verify 报告: `reports/conan-verify-report.md`（G0-G4 + L2/L4/L5 全 PASS）
- conan create 日志: `reports/conan-create.log`

## 真机验证记录

验证环境: OpenDesk 真机（OpenHarmony PC aarch64, clang 15, libc++, conan 2.29.1 适配版）

桌面侧预验证（Windows g++ 13，4 变体编译+运行）已通过；真机检查点（以实际日志为准回填）:
1. `ctest --output-on-failure` 为 `4/4`，名称为 test-cpp98/cpp11/cpp14/cpp17，每变体
   `All 40 selected tests passed.`
2. `test_any_lite` 与 `test_any_lite_cpp11` 均由 test_package 实际运行并退出 0
3. `conan-verify` 的 G0-G4/L2/L4/L5 全部通过

---

**编译结束**: 2026-09-24
**最终状态**: published
