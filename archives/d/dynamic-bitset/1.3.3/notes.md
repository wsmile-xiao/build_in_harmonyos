# dynamic-bitset 1.3.3 适配笔记

## 编译环境
- **类型**: header-only C++17（无库编译）
- **编译日期**: 2026-08-28
- **编译器**: clang 15（OHOS 6.0 交叉工具链）
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built

## 编译步骤（conan create 全流程）

```bash
conan create archives/d/dynamic-bitset/1.3.3 --build=missing
```

### 1. 源码获取（source()）
`get()` 下载 GitHub v1.3.3 tag tarball（50KB），`strip_root=True` 解压。

### 2. 打包（package()）
header-only——拷贝 `include/sul/dynamic_bitset.hpp`（单头文件）到 include。

### 3. 上游测试（build() 集成——rule 4 实测回填）
Catch2 v3 单元测试（tests/ 依赖 Catch2/libpopcnt **子模块**——tarball 不含）——
从 GitHub 下载 Catch2 源码到 `extlibs/Catch2`；`DYNAMICBITSET_BUILD_TESTS=ON`
单独构建 + ctest 运行：
```bash
cmake <src> -DDYNAMICBITSET_BUILD_TESTS=ON -DDYNAMICBITSET_BUILD_DOCS=OFF \
  -DCATCH_BUILD_STATIC_LIBRARY=ON \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++ \
  -DCMAKE_CXX_FLAGS='-std=c++17'
cmake --build <bdir> -j4
ctest --test-dir <bdir>
```
- aarch64 OHOS 直接可编译（header-only 无平台限制）
- subprocess 调 cmake/ctest 用绝对路径（OHOS posix_spawn 不按 PATH 搜索
  相对名——与 rich/vc 同源教训）

**实测结果（rule 4 如实记录——上游测试无法完整运行）**：
- **Catch2 版本兼容性排查（5 轮实测）**：
  1. v2.13.10：无 generators 布局（dynamic-bitset 测试需
     `catch2/generators/catch_generators.hpp`）——configure 失败
  2. v3.2.1/v3.3.2/v3.4.0：无 `catch_uniform_integer_distribution.hpp`
     （测试 include 它）——build 失败
  3. v3.5.0：**唯一含所需全部头文件的版本**——但与 OHOS LP64/clang 15
     编译不兼容：
     - `SizedUnsignedType<16>` 缺特化（`DoubleWidthUnsignedType_t` =
       `2*sizeof(T)`，8 字节类型需 16 字节特化——v3.5.0 只特化到 8）
     - generic `extendedMult` static_assert `sizeof(unsigned long long) <
       sizeof(unsigned long)` 失败（LP64 下均为 8 字节）
  → 上游测试无法在 OHOS 上完整运行——**如实记录 N/A**，R34 消费验证兜底

## 验证结果
- **构建**: `dynamic-bitset/1.3.3: Package created`
- **上游测试**: N/A（Catch2 v3.5.0 与 OHOS LP64/clang 15 编译不兼容——5 轮
  版本排查如实记录，rule 4）
- **R34 消费者验证**: test_package——头文件存在 + sul::dynamic_bitset 位操作
  smoke（1/1 = 100%）
