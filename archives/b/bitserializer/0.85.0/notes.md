# bitserializer 0.85.0 适配笔记

## 编译环境
- 构建系统: cmake（CMakeLists.txt，C++17 header-only 核心）
- 编译日期: 2026-09-03
- 编译器: clang/clang++ 15.0.4（/data/service/hnp/bin，libc++）
- 状态: built

## 编译步骤

```bash
# 1. init-build（bootstrap）：下载官方 tag v0.85 tarball 并解压
ohc-run.py init-build bitserializer 0.85.0 --url=https://github.com/PavelKisliak/BitSerializer/archive/refs/tags/v0.85.tar.gz

# 2. 手动编译验证（上游测试，BUILD_TESTS=ON，GTest 1.17.0 来自 ohpcd 制品仓）
cmake .. -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTS=ON -DBUILD_SHARED_LIBS=OFF -DCMAKE_INSTALL_PREFIX=<prefix> -DCMAKE_PREFIX_PATH=<gtest-pkg>
make -j4 && ctest          # 860/860 通过

# 3. 配方验证（ohos-aarch64 profile）
ohc-run.py conan-verify bitserializer 0.85.0   # G0-G4 + L2/L4/L5 全过

# 4. finish（含 W2/W3 本地 CI 模拟）
ohc-run.py finish bitserializer 0.85.0 published
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan create 时 `from_chars` 报 "call to deleted function" | OHOS libc++ charconv 无浮点 from_chars 实现，上游按 clang 版本误判能力宏 | 补丁 0001：`__OHOS__` 下关闭 `BITSERIALIZER_HAS_FLOAT_FROM_CHARS`，浮点转换走 convert_compatibility.h 的 strtod/snprintf 回退 |
| 2 | test_package 编译报 `basic_string_view` 不在 std 命名空间 | libcxx-ohos 裁剪传递包含，text.h 只 include <cstddef> 却用 basic_string_view | 补丁 0002：text.h 显式 include <string_view> |
| 3 | 上游测试工具 perf_utils.cpp 报 pthread_setaffinity_np 未声明 | OHOS musl 无 GNU pthread affinity 扩展（知识库 E211 已覆盖） | 测试工具内改用 sched_setaffinity(0, ...)；不纳入 conandata patches（CI 不构建测试） |
| 4 | auto_fixture.h std::max/min 参数类型冲突（long long vs int64_t） | OHOS libc++ chrono rep 为 long long，int64_t 为 long | 测试工具内 static_cast<int64_t> 统一；不纳入 conandata patches |

## 源码修改

- `patches/0001-cmake-bitserializerConfig.h.in.patch`：config.h.in 宏判断按 `__OHOS__` 关闭浮点 from_chars
- `patches/0002-include-bitserializer-common-text.h.patch`：text.h 显式包含 `<string_view>`
- 测试工具（perf_utils.cpp / auto_fixture.h）修复仅用于本地上游测试，未入配方补丁

## 依赖版本

- gtest/1.17.0（测试期，来自 ohpcd 制品仓）
- 运行时/库本体：无外部依赖（header-only）

## 验证结果

```bash
ctest --output-on-failure   # 860/860 通过（unit 834 + integration 26）
conan-verify bitserializer 0.85.0   # G0-G4 + L2/L4/L5 全过
```

## 注意事项

- bitserializer 核心为 header-only（CMake INTERFACE 库），配方 `package_type: header-library`，分发 `BitSerializer::core` 目标与头文件。
- 浮点回退路径（strtod/snprintf）与 from_chars 在精度/格式上有细微差异（locale、%g 位数），一般序列化场景可接受。
- 本任务新增 2 条知识草稿：`DRAFT-bitserializer-0.85.0-ohos-float-from-chars-fallback`、`DRAFT-bitserializer-0.85.0-libcxx-transitive-include-string-view`（路径 B）。

---

**编译结束**: 2026-09-03
**最终状态**: built
