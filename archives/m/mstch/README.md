# mstch

[mstch](https://github.com/no1msd/mstch) 是 Daniel Sipka 用 C++11 实现的
{{mustache}} 模板库，依赖 Boost（boost::variant / boost::optional）。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 1.0.2 | ✅ 已适配 | OHOS AArch64 clang + libc++/musl，上游测试 65/65 通过 |

## 依赖

- `boost` (>= 1.54, `boost_variant` / `boost_optional`) — 编译期与运行期依赖，由 Conan 解析
- 上游单元测试（Catch v1.12.2, rapidjson, headerize, mustache/spec）仅在 `build()`
  中按 1.0.2 tag 固定的 submodule SHA 拉取，**不进入 package**
- `test_package` 无第三方依赖（纯 mstch 公共 API + 标准库）

## 构建说明

- 上游 CMake `WITH_UNIT_TESTS=ON` 完整编译并执行官方测试套件（`mstch_test`，Catch v1.12.2）
- 唯一 patch 仅提升 `cmake_minimum_required` 3.0.2 → 3.5...3.31（CMake 兼容性，
  不涉及模板渲染逻辑）
- musl 下需注入 `-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE`（上游 CI 的已知规避项，
  见 conanfile.py `extra_cxxflags` 注释）
