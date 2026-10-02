# daw_json_link 3.38.1 适配笔记

## 编译环境
- 构建系统: cmake（header-only CMake INTERFACE library）
- 编译日期: 2026-09-19
- 编译器: clang/clang++ 15.0.4（OHOS aarch64，/data/service/hnp/bin）
- 状态: published

## 背景

daw_json_link 是任务 #13783（wave7 轻件）指定件。C++17 静态 JSON 解析/序列化库，
通过 json_data_contract 数据契约实现编译期绑定。

依赖核验（2026-09-19 实测）：
- daw-header-libraries/2.135.0 → 制品仓已发布 ✅（直接可用）
- daw-utf-range/2.2.6 → 制品仓无、任务池无、无 PR → **依赖断链**
  - 处置：按 R36/PF4 不捎带原则，先行独立适配 daw-utf-range（calbee21 账号，
    任务 #13788，PR 详见其归档），本包在其合入发布后构建

## 编译步骤

```bash
# 源码: beached/daw_json_link v3.38.1（官方 tag）
# SHA-256: 8de522747e51954daa47f9b7e9b0258fa361f419a7ff170aa548a959ec52b514

# 配方验证（OHOS aarch64 profile，依赖走 Conan）
conan create archives/d/daw_json_link/3.38.1 \
  -pr:h ~/.conan2/profiles/ohos-aarch64 -pr:b default --build=missing
# → 构建 + test_package 消费者测试 PASS（from_json/to_json/json_value 契约往返）

# 上游测试（本地联网补跑，DAW_ENABLE_TESTING=ON + DAW_JSON_USE_BOOST=OFF）
# 见「验证结果」节
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | extern/ 默认 FetchContent 拉 daw-header-libraries/utf_range | 上游 extern/CMakeLists.txt | CMakeToolchain 注入 `DAW_USE_PACKAGE_MANAGEMENT=True`，改走 find_package（依赖由 Conan CMakeDeps 提供） |
| 2 | 上游 tests 默认 find_package Boost 1.83 | tests/CMakeLists.txt DAW_JSON_USE_BOOST 默认 ON | 本地补跑用 `-DDAW_JSON_USE_BOOST=OFF`（可选 vc/Boost 集成关闭——任务指定"可能有可选 vc——关"） |
| 3 | 上游测试数据集走 FetchContent（cities.json 等） | 根 CMakeLists DAW_ENABLE_TESTING 分支 | 本地联网补跑（FETCHCONTENT_UPDATES_DISCONNECTED）拉取 test_data release 分支 |
| 4 | cookbook_output_flags1_test / daw_json_writer_test 2 项编译失败 | **平台 libc 头差异**：OHOS musl sysroot stdio.h 的 `stdout` 宏展开为 `_IO_FILE *const`，`to_json(v, stdout)`/`json_writer(stdout)` 的 serialization_policy 构造要求非 const 第 1 参数（would lose const qualifier）——glibc 下 stdout 是运行时表达式无此问题 | 非适配缺陷（配方产物不含测试），豁免并最小复现留证（probe2.cpp 同款调用单文件复现 error）；其余 145/147 测试全过 |

## 源码修改

无需补丁（header-only 库，无平台适配代码修改）。

## 依赖版本

- daw-header-libraries/2.135.0（制品仓已发布）
- daw-utf-range/2.2.6（本批先行适配发布，见 archives/d/daw-utf-range/2.2.6）

## 验证结果

```bash
# conan create + test_package（消费者测试）
# → PASS: daw_json_link header-only 库链接和核心 API 验证通过
#   覆盖: json_data_contract 契约定义 / from_json 解析 / to_json 序列化
#         （daw-utf-range 路径覆盖）/ json_value 动态访问 / 序列化往返

# 上游 ctest（本地联网补跑，147 测试注册口径，DAW_JSON_USE_BOOST=OFF）
# → 145/147 通过（98.6%）
# → 2 项豁免（Not Run）：cookbook_output_flags1_test / daw_json_writer_test_test
#   根因: OHOS musl sysroot stdout 宏 const 限定 → serialization_policy 构造
#         "would lose const qualifier"（平台 libc 头差异，最小复现 probe2.cpp 已留证，
#         同家族见 knowledge/drafts/DRAFT-nvtx-3.6.0-...-stdout-recursive-macro-werror.md）
```

## 注意事项

- header-only 库，package_type = header-library，cpp_info.libs 为空。
- CMake 目标: daw::daw-json-link（install EXPORT NAMESPACE daw::）。
- OHOS 适配: generate() 中 os in ("Linux","OHOS") 时注入 CMAKE_SYSTEM_NAME=Linux + CMAKE_SYSTEM_PROCESSOR=aarch64（R32）。
- 上游 CMake 安装目录用 `${CMAKE_INSTALL_DATAROOTDIR}/${PROJECT_NAME}/cmake`。

---

**编译结束**: 2026-09-19
**最终状态**: published
