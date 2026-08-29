# rapidcsv 9.07 适配笔记

## 编译环境
- **类型**: header-only C++11（无库编译）
- **编译日期**: 2026-08-28
- **编译器**: clang 15（OHOS 6.0 交叉工具链）
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built

## 编译步骤（conan create 全流程）

```bash
conan create archives/r/rapidcsv/9.07 --build=missing
```

### 1. 源码获取（source()）
`get()` 下载 GitHub v9.07 tag tarball（225KB），`strip_root=True` 解压。

### 2. 打包（package()）
header-only——拷贝 `src/rapidcsv.h`（单头文件）到 include。

### 3. 上游测试（build() 集成——rule 4 实测回填）
自定义 unittest 框架（tests/unittest.h + test00X.cpp + CSV 样本；2 个 perf
test：test001~test110 单元测试 + ptest001/ptest002 perf——**必须 Debug 构建**
（上游 add_unit_test 宏只在 CMAKE_BUILD_TYPE=Debug 注册）——`RAPIDCSV_BUILD_TESTS=ON`
单独构建 + ctest 运行：
```bash
cmake <src> -DRAPIDCSV_BUILD_TESTS=ON \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++ \
  -DCMAKE_CXX_FLAGS='-std=c++11'
cmake --build <bdir> -j4
ctest --test-dir <bdir>
```
- aarch64 OHOS 直接可编译（header-only 无平台限制）
- subprocess 调 cmake/ctest 用绝对路径（OHOS posix_spawn 不按 PATH 搜索
  相对名——与 rich/vc 同源教训）

**实测结果：112 passed / 0 failed / 0 skipped（112 用例 = 100%，分母=全部用例）**

关键处理（缺依赖就装上 / 环境差异修复）：
1. **CSV 样本拷贝**：ptest001/002 读 `../tests/msft.csv`（相对 ctest 工作
   目录 build-tests → build/Release/tests/msft.csv 不存在——
   `ios_base::clear: unspecified iostream_category error` 实测）——把源码
   tests/*.csv 样本拷贝到相对位置后 112/112 通过

## 验证结果
- **构建**: `rapidcsv/9.07: Package created`
- **上游测试**: 实测 **112/112 通过（100%）**——build() 集成回填（rule 4，分母=全部 112 用例；Debug 构建全量 test001~110 + ptest001/002）
- **R34 消费者验证**: test_package——头文件存在 + Document 读 CSV smoke（1/1 = 100%）
