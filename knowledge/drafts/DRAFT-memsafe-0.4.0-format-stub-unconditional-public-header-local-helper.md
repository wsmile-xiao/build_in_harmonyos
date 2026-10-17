# DRAFT：公开头无条件 std::format —— __cpp_lib_format 守卫 + 零依赖本地替代

- **草稿 ID**: DRAFT-memsafe-0.4.0-format-stub-unconditional-public-header-local-helper
- **来源库**: memsafe 0.4.0（任务 memsafe-0.4.0-r01-pc2-17）
- **判定**: 路径 B（知识库扩展候选；既有条目覆盖守卫面，本候选的新增差异经消费者实测验证可跨库复用）

## 问题

OHOS SDK 26.0.0.18 的 clang15 标准库（libcxx-ohos）提供 `<format>` 头文件但
`std::format` 未实现（`_LIBCPP_HAS_NO_INCOMPLETE_FORMAT`，`__cpp_lib_format` 未导出）。
与用 `__has_include(<format>)` 守卫的库（enchantum/microsoft-proxy 案例）不同，
memsafe.h 是**无条件** `#include <format>` 并直接调用 `std::format` 的**公开 API 头**
（错误消息构造行 `throw memsafe_error(std::format("try_lock{} timeout", ...))`），
任何消费者 include 该头即编译失败。

## 根因

- libcxx-ohos 提供占位 `<format>` 头：头存在 ≠ 功能可用；
- memsafe.h 的调用点在正常代码路径上（非可选特性），只改守卫让功能缺席不可行；
- 首次错误：`memsafe.h:393:46: error: no member named 'format' in namespace 'std'`，
  命令 `clang++ -std=c++20 -c consumer.cpp`，cwd=`$HOME/tmp/builds/memsafe-0.4.0.work`，退出码 1；
- 探针确认：`__cpp_lib_format` 未定义（feat_probe 输出 `no __cpp_lib_format`）。
- 同头附带 clang15 严格解析错误：`missing 'typename' prior to dependent type name 'T::ValueType'`（3 处）。

## 方案

1. 无条件 `#include <format>` 改为 `#ifndef __cpp_lib_format` 守卫（完整工具链照旧 include）；
2. 守卫内提供最小**零依赖**本地替代函数 `ms_fmt1`（纯字符串单占位符 "{}" 替换），
   原调用点改为 `ms_fmt1("try_lock{} timeout", read_only ? " read only" : "")`；
   time_point 序列化用 `to_string((long long)tp.time_since_epoch().count())`；
3. 依赖类型补 `typename`（`typename T::ValueType` 等 3 处）；
4. 补丁属 libc 能力探测类（R8 例外），非平台宏，完整 libc++ 工具链同样可编译。

「不引 fmt 依赖」是本方案与既有 `std::format → fmt::format` 替换（DRAFT-stdformat-to-fmt）
的关键差异：单点/少量调用点场景不必引入新依赖与链接侧处理。

## 验证

- 消费者程序（memsafe::Shared/Weak/Locker 公开 API）编译链接运行 exit 0；
- test_package test.cpp 输出 `test_memsafe: OK (shared=7, weak=7)`，exit 0；
- conan create 干净构建（G2）通过；conan-verify G1/G2/G3/G4 全 PASS；
- 上游 gtest 8/11 通过（另 3 项：Sizes 为平台 ABI sizeof 断言差异，Plugin/Cycles 需
  clang-20 插件硬阻塞，均与本补丁无关）。

## 适用边界

- **适用**：OHOS SDK 26.0.0.18 / clang15 / libcxx-ohos 工具链上，公开 API 头或
  header-only 库直接无条件调用 std::format 的 C++20 项目；也适用于同头内
  clang15 严格解析要求的依赖类型 typename 补齐。
- **反例/不适用**：库只有测试/可选路径用 format（用 `__has_include` 守卫即可，走 E557）；
  库里 format 调用点多且需完整语义（应走 fmt 替换 + 链接侧处理，见
  DRAFT-stdformat-to-fmt-substitution-downstream-effects）。