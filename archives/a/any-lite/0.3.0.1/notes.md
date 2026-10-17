# any-lite 0.3.0.1 — 适配笔记（上游 0.3.0）

## 来源核验（bootstrap 阶段，官方资料确认）
- 官方仓库：https://github.com/martinmoene/any-lite （GitHub 跳转到 nonstd-lite/any-lite 组织）
- 正式标签：`v0.3.0` → commit `8f7c53c605cc51d067a16c06054a7a4c23945a10`
- Release 发布时间：2020-11-28T08:21:12Z
- 许可证：Boost Software License 1.0（BSL-1.0）
- 源码 tarball：`https://github.com/martinmoene/any-lite/archive/refs/tags/v0.3.0.tar.gz`
- SHA-256：`fa7087ef7b4455c00b4b715649eb7176d6d0806c3a57cd4734845611ebe9888e`

## 结构
- 单文件头文件库：`include/nonstd/any.hpp`
- CMake INTERFACE library：目标 `nonstd::any-lite`，包 `any-lite`
- CMake 选项：`ANY_LITE_OPT_BUILD_TESTS` / `ANY_LITE_OPT_BUILD_EXAMPLES` / `ANY_LITE_OPT_SELECT_STD` / `ANY_LITE_OPT_SELECT_NONSTD`
- 上游自带 Conan 1.x 配方（`from conans import ...`）；本归档按 Conan 2.x 重写（optional-lite 同款模式）
- 上游测试使用 lest 框架：`test/any.t.cpp`

## 依赖
- 无任何第三方依赖（仅标准库）

## 上游测试

- 上游 `test/` 通过 CMake 注册 4 个 CTest 变体：`test-cpp98`、`test-cpp11`、
  `test-cpp14`、`test-cpp17`。
- 每个变体共同链接 `test/any.t.cpp` 与 `test/any-main.t.cpp`，未修改上游测试文件。
- `conanfile.py` 的 `build()` 无条件调用 `cmake.test()`，四个 CTest 变体会
  在构建环境中真实编译并执行，失败会直接阻断 `conan create`。

## 消费者测试

- `test_package/test_any_lite.cpp`：C++17 消费者，验证包发现、链接与基础 API。
- `test_package/test_any_lite_cpp11.cpp`：C++11 消费者，验证非 `std::any`
  回移实现、指针 `any_cast`、`type()` 与 `bad_any_cast` 异常路径。

## 待设备验证

本机没有 Conan/CMake/OHOS 工具链，不能给出新的执行结果。需要在 OpenDesk
设备完成 `conan create` / `conan-verify`，确认以下结果后再以日志回填 PR：

```bash
export CONAN_HOME="$HOME/tmp/ch/home-any-lite"
python3 scripts/ohc-run.py conan-verify any-lite 0.3.0.1
```

预期检查点：

1. `ctest --output-on-failure` 为 `4/4`，名称为
   `test-cpp98/cpp11/cpp14/cpp17`；
2. `test_any_lite` 与 `test_any_lite_cpp11` 均由 test_package 实际运行并退出 0；
3. `conan-verify` 的 G0-G4/L2/L4/L5 全部通过后，才把最终日志、耗时和
   `build_date` 写回本文件及版本级 manifest。

---

**编译结束**: 2026-08-31
**最终状态**: built
