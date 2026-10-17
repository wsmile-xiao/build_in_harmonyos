# DRAFT-ethash-1.1.0-test-package-cxx-consumer-cpp-static-lib

> 草稿（Path B 知识库扩展候选），由 ethash 1.1.0 适配产生，与同名 `.kv` 配对、逐字段一致。
> 仅为本地知识草稿，不代表任何 PR/Issue/commit/push/CI/review/merge/score 已成功。

## topic

C-API + 内部 C++ 实现的静态库，其 Conan `test_package` 消费者工程必须用 CXX 工程（或显式链接
C++ 运行时）；C 工程直接链接该类静态库会报 C++ 运行时符号 undefined。

## error_signature

```text
ld.lld: error: undefined symbol: __cxa_begin_catch
>>> referenced by ethash.cpp
>>>               ethash.cpp.obj:(__clang_call_terminate) in archive .../libethash.a
ld.lld: error: undefined symbol: std::terminate()
>>> referenced by ethash.cpp
>>>               ethash.cpp.obj:(__clang_call_terminate) in archive .../libethash.a
ld.lld: error: undefined symbol: __gxx_personality_v0
clang-15: error: linker command failed with exit code 1 (use -v to see invocation)
```

## root_cause

`test_package/CMakeLists.txt` 被模板生成为 `project(test_ethash C)` + `test.c`。ethash 公开
C API（`ethash.h`/`keccak.h`，`extern "C"`），但静态库 `libethash.a` 内含 C++ 实现对象
（`ethash.cpp`、`global_context.cpp`）与 `-fno-rtti` 编译，链接期需要 libc++ 运行时符号
（`__cxa_begin_catch`、`std::terminate`、`__gxx_personality_v0`）。C 工程使用 C 链接器，
不自动携带 C++ 运行时 → 全部 undefined。

## durable_solution

1. `test_package/CMakeLists.txt`：`project(test_ethash CXX)`，测试源改 `test.cpp`。
2. 测试源继续只调用被测包的公开 C API（C 兼容写法在 C++ 中合法），或直接使用 C++ API。
3. 保持 `target_link_libraries(test_ethash ethash::ethash)` 不变；CMake 因 project 为 CXX
   自动选择 C++ 链接器并携带 libc++。
4. 不要用 C 工程 + `-lstdc++`/`-static-libstdc++` 硬拼（非 CMake 工程语言方式，脆弱且
   E455 类 libcxx 配置问题易混入）；首选工程语言 CXX。

## impact

ethash 修复前：G2 `conan create` 在 test_package build 阶段链接失败（`Error 2`），
W3/CI 无法通过。修复后：conan-verify 全门禁 PASS、CTest `test_ethash` 4 项消费者断言 PASS。

## recovery_condition

若被测包同时暴露纯 C 与 C++ API，C 消费者仍可用 C 工程但必须显式链接 C++ 运行时；本方案
面向 test_package 默认模板（C 工程）的通用修复，无需修改库侧。

## evidence_references

- `archives/e/ethash/1.1.0/reports/conan-verify-report.md`（G2 PASS）
- `archives/e/ethash/1.1.0/reports/conan-create.log`（修复前 undefined 符号、修复后 test PASS）
- `archives/e/ethash/1.1.0/test_package/test.cpp`、`test_package/CMakeLists.txt`

## relations

- similar_to: E247（pkg-config 侧同类根因：静态 C API 归档缺 C++ 运行时元数据）
- caused_by: C 消费者 × C++ 静态库链接模型
- conflicts_with: —
