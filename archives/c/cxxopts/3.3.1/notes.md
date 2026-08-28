# cxxopts 3.3.1 适配笔记

## 编译环境
- **类型**: header-only C++11/14（无库编译）
- **编译日期**: 2026-08-28
- **编译器**: clang 15（OHOS 6.0 交叉工具链）
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built

## 编译步骤（conan create 全流程）

```bash
conan create archives/c/cxxopts/3.3.1 --build=missing
```

### 1. 源码获取（source()）
`get()` 下载 GitHub v3.3.1 tag tarball（161KB），`strip_root=True` 解压。

### 2. 打包（package()）
header-only——拷贝 `include/cxxopts.hpp`（单头文件）到 include。

### 3. 上游测试（build() 集成——rule 4 实测回填）
Catch2 单元测试（test/ 目录——**自带 catch.hpp，无需网络下载**；3 个 ctest
用例：options/find-package-test/add-subdirectory-test）——`CXXOPTS_BUILD_TESTS=ON`
单独构建 + ctest 运行：
```bash
cmake <src> -DCXXOPTS_BUILD_TESTS=ON -DCXXOPTS_BUILD_EXAMPLES=OFF \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++ \
  -DCMAKE_CXX_FLAGS='-std=c++14'
cmake --build <bdir> -j4
ctest --test-dir <bdir>
```
- aarch64 OHOS 直接可编译（header-only 无平台限制）
- subprocess 调 cmake/ctest 用绝对路径（OHOS posix_spawn 不按 PATH 搜索
  相对名——与 rich/vc 同源教训）

**实测结果：36/38（94.7%）**——options_test 实测 34 test cases 全过（208
assertions）+ find-package/add-subdirectory 2 个 CMake 集成测试通过；4 个
TEST_CASE 因 #ifdef CXXOPTS_HAS_OPTIONAL/FILESYSTEM 条件编译排除（非失败）

关键处理（缺依赖就装上 / 环境差异修复）：
1. **CMAKE_BUILD_TYPE 显式 Release**：初测 1/3——test/CMakeLists.txt 的
   ctest `-C ${CMAKE_BUILD_TYPE}` 为空报 'Invalid value used with -C'
   （find-package-test/add-subdirectory-test 失败实测）——显式
   `-DCMAKE_BUILD_TYPE=Release` 后 3/3 通过

## 验证结果
- **构建**: `cxxopts/3.3.1: Package created`
- **上游测试**: 实测 **36/38 通过（94.7%）**——options_test 34 test cases 全过 + 2 个 CMake 集成测试通过；4 个 TEST_CASE 条件编译排除（rule 4，分母=全部 38 用例）
- **R34 消费者验证**: test_package——头文件存在 + cxxopts::Options 解析 smoke（1/1 = 100%）
