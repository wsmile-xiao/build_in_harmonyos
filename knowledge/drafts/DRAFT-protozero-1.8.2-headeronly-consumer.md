# DRAFT-protozero-1.8.2-headeronly-consumer：protozero header-only 适配经验

> Contributor: pc1-41 | Status: Draft | Updated: 2026-08-28
> Source: protozero 1.8.2 Bootstrap + Adapt + 本地验证（首轮 G2 调试与修复）

## 现象

- `conan create`（test_package）首次失败：`no matching member function for call to
  'add_packed_uint32'` → 改用 `add_packed_varint` → `'add_packed_varint' is a private
  member` → 改用公开 `packed_field_uint32` 后，test() 阶段仍抛
  `protozero::invalid_tag_exception: invalid tag exception`（仅 `-DNDEBUG` 构建复现）。
- 直接编译（不带 `-DNDEBUG`）运行同一 `test_pbf.cpp` 却通过；加入 `-O3 -DNDEBUG` 后复现崩溃。

## 根因

1. **Getter 失步陷阱**：protozero 的 `get_uint32/get_string/get_packed_*` 会推进
   `pbf_reader` 内部状态机。若把 getter 调用写在 `assert(...)` 内，`-DNDEBUG`
   （conan create 默认 `-O3 -DNDEBUG`）会整段删除调用 → reader 未前进 → 下一条目
   把字段值字节当 tag 解析，tag 0 触发 `invalid_tag_exception`。
2. **Packed 写入 API 边界**：该版本无 `add_packed_uint32`；`add_packed_varint` 是
   `basic_pbf_writer` 私有成员；必须用公开 `packed_field_uint32`/`packed_field_varint`
   辅助类 `add_element(...)`。
3. **子写器提交时机**：packed 子写器通过析构（`close_submessage`）写回长度；必须先让
   子写器析构/`commit()`，再构造 `pbf_reader` 读回 buffer。

## 方案

- header-only 库 Conan 配方：`package_type = "header-library"`，`package_info()` 不声明
  libs，暴露 `protozero::protozero` CMake target；`generate()` 设 `BUILD_TESTING=OFF`
  使配方构建自包含（无需 protobuf）。
- test_package：getter 一律无条件执行、结果存变量后再 `assert`；packed 用公开辅助类
  写入并在读回前确保子写器析构。

```cpp
uint32_t v1 = reader.get_uint32(); assert(v1 == 42u);   // 不是 assert(reader.get_uint32() == 42u)
...
{ protozero::packed_field_uint32 packed(writer, 3); packed.add_element(1u); }
// packed 析构提交后，再构造 pbf_reader 读回 buffer
```

## 验证

- `clang++ -std=c++17 -fPIC -O2 -stdlib=libc++ -O3 -DNDEBUG -isystem <pkg>/include test_pbf.cpp`
  编译运行输出 `protozero 1.8.2 test_package: OK`（exit 0）。
- `python3 scripts/ohc-run.py conan-verify protozero 1.8.2` → G1/G0/G2/G3/G4/L2/L4/L5 全通过，
  verdict `配方验证通过`。

## 适用边界

- header-only C++ 库 Conan/CMake 消费；protozero 或同类“getter 推进读取状态”的流式解析库。
- CI/conan create 采用 `-O3 -DNDEBUG` 的环境必须按本方案写 test_package。

## 相关事实（本轮证据）

- 官方仓库 https://github.com/mapbox/protozero，tag v1.8.2，官方归档
  https://github.com/mapbox/protozero/archive/refs/tags/v1.8.2.tar.gz，
  SHA-256 `68d1df951b4d8397355c8fc9ffed40d9c06282a877fe847403feac6edcee3ef1`。
- `protozero/pbf_reader.hpp` 是 OSRM v26.5.0 明确依赖并加入系统 include 的头文件。
- 上游测试：`ctest` 9/9 通过（reader_tests/unit_tests/pbf-decoder×7）；`writer_tests`
  在未找到 protobuf 时上游自动禁用（可选入口，非本包缺失依赖）。

## 查重差异

- E225/E298 涉及 CMakeToolchain preset 布局与 cmake.test() 委托 CTest 的 conanrun 环境，
  与本条目的 NDEBUG getter 失步 + header-only 消费边界不同主题；本条为独立新增草稿。
