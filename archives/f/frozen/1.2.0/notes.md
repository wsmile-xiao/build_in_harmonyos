# frozen 1.2.0 适配笔记

## 编译环境
- **类型**: header-only C++14（无库编译）
- **编译日期**: 2026-08-28
- **编译器**: clang 15（OHOS 6.0 交叉工具链）
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built

## 编译步骤（conan create 全流程）

```bash
conan create archives/f/frozen/1.2.0 --build=missing
```

### 1. 源码获取（source()）
`get()` 下载 GitHub 1.2.0 tag tarball（187KB），`strip_root=True` 解压。

### 2. 打包（package()）
header-only——`shutil.copytree` 拷贝 `include/frozen/` 头文件目录
（map/set/unordered_map/unordered_set/string/algorithm 等）到 include。

### 3. 上游测试（build() 集成——rule 4 实测回填）
Catch2 单元测试（tests/ 目录——**自带 catch.hpp，无需网络下载**；frozen.tests
目标内含 **56 个 TEST_CASE**（13 个 test_*.cpp）+ no_exceptions 编译测试）——`FROZEN_BUILD_TEST=ON` 单独构建 +
ctest 运行：
```bash
cmake <src> -DFROZEN_BUILD_TEST=ON \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++ \
  -DCMAKE_CXX_FLAGS='-std=c++14'
cmake --build <bdir> -j4
ctest --test-dir <bdir>
```
- aarch64 OHOS 直接可编译（header-only 无平台限制）
- subprocess 调 cmake/ctest 用绝对路径（OHOS posix_spawn 不按 PATH 搜索
  相对名——与 rich/vc 同源教训）

**实测结果：56 passed / 0 failed / 0 skipped（56 用例 = 100%，分母=全部用例）**

## 验证结果
- **构建**: `frozen/1.2.0: Package created`
- **上游测试**: 实测 **56/56 通过（100%）**——build() 集成回填（rule 4，分母=全部 56 用例；frozen.tests 56 TEST_CASE 全过 + no_exceptions 通过）
- **R34 消费者验证**: test_package——头文件存在 + frozen::map constexpr 构造 smoke（1/1 = 100%）
