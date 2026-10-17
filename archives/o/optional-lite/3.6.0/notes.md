# optional-lite 3.6.0 适配笔记

## 基本信息
- **上游**: https://github.com/nonstd-lite/optional-lite （原名 martinmoene/optional-lite，已 301 永久重定向改名；两个 URL 下载内容 SHA256 一致，实测 3.5.0 tarball 双 URL 同为 6077cee8…）
- **版本**: 3.6.0
- **任务分支**: feat/optional-lite-3.6.0
- **许可证**: BSL-1.0 (Boost Software License)
- **类型**: header-only C++ 库 (CMake INTERFACE library)
- **前置版本**: 本仓库已有 3.5.0 归档（75 用例口径），本任务为版本升级适配

## 3.6.0 相对 3.5.0 的变化
- 新增 `value_or_eval(F)` 扩展 API（`optional_CONFIG_NO_EXTENSIONS=0` 时可用）：非空返回包含值、空返回 `f()`；提供 `const&`/`&&`（C++11 ref-qualifier）与 C++98 `const` 三种重载
- 新增 emplace 的 const 变体等 7 个上游测试用例（75 → 82 功能用例）
- 无 breaking change，消费者 API 兼容

## 依赖
无任何依赖，仅包含单个头文件 `include/nonstd/optional.hpp`。

## 构建系统
CMake，header-only INTERFACE library。
- `OPTIONAL_LITE_OPT_BUILD_TESTS=ON` 启用上游测试
- 上游测试使用 lest 框架（内置于 `test/lest/lest_cpp03.hpp`），无需网络
- clang 下 CTest 构建 4 个变体: cpp98/cpp11/cpp14/cpp17

## 安装产物
- 头文件: `include/nonstd/optional.hpp`
- 许可证: `licenses/LICENSE.txt`
- CMake 目标: `nonstd::optional-lite`（配方直接 copy 头文件与 LICENSE，等价于上游 cmake install 的接口部分）

## 上游测试统计（四类数字口径）

1. **上游源码静态声明总数: 88 个 lest CASE**
   - `test/optional.t.cpp`: 82 个功能用例（逐个 `grep -c 'CASE('` 统计）
   - `test/optional-main.t.cpp`: 6 个诊断用例（版本/配置/编译器/语言/库特性报告）
   - 交叉验证: `optional-lite-cpp17.t --list-tests '*'` 输出 88 行，与静态统计一致
2. **官方套件实际执行数: 4 变体 × 74 用例 = 296 次用例执行，全部通过**
   - ctest 汇总: `100% tests passed, 0 tests failed out of 4`（test-cpp98/cpp11/cpp14/cpp17）
   - 每个变体 lest 输出 `All 74 selected tests passed.`
3. **未执行/跳过数: 每变体 14 个用例（4 变体共 56 次未执行）**
   - 全部是带 `.` 前缀隐藏标签的用例（lest 默认不选中，上游有意设计，非 OHOS 平台原因）:
     6 个诊断（`[.optional][.version]` 等）、2 个 `[.]`（alignment_of/storage_t sizeof 展示）、
     1 个 `[.issue-1]`、5 个 `[.issue-61-*]`（invalid detection 诊断）
   - cpp98 与 cpp17 注册的用例列表完全一致（C++11-only 用例在 cpp98 下同样注册，断言体内部用
     `#if optional_CPP11_OR_GREATER` 条件编译），因此四个变体执行数相同
4. **新增 test_package 消费者测试: 2 个程序 11 个断言，全部通过**
   - `test_optional_lite.cpp`（C++17，默认 std::optional 模式）: 8 个断言——空/有值 optional、
     value()、value_or()、make_optional、重新赋值、reset、emplace
   - `test_optional_lite_ext.cpp`（C++14，nonstd 回移实现模式）: 3 个断言——3.6.0 新增
     `value_or_eval()` 的非空/空/右值行为，并静态断言 C++14 下确实使用 nonstd 实现

## OHOS 适配
- E092: CMake 不识别 OHOS。配方 generate() 中设置 `CMAKE_SYSTEM_NAME=Linux` +
  `CMAKE_SYSTEM_PROCESSOR=aarch64`（R32: `settings.os in ("Linux", "OHOS")` 判断）
- `CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY` 避免 header-only 项目的编译器探测链接步骤
- 无需补丁，源码直接编译；`patches: []`
- 本机（aarch64 鸿蒙）conan create 时 can_run 为真，上游测试与消费者测试均真实执行

## 验证命令
```bash
export CONAN_HOME="$HOME/tmp/ch/home-optlite"
export SSL_CERT_FILE="$HOME/usr/local/ssl/cert.pem"
python3 scripts/ohc-run.py conan-verify optional-lite 3.6.0
# conan create: -pr:h/-pr:b ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
```
- conan-verify 报告: `reports/conan-verify-report.md`（G0-G4 + L2/L4/L5 全 PASS）
- conan create 日志: `reports/conan-create.log`
---

**编译结束**: 2026-09-05 23:55
**最终状态**: built
