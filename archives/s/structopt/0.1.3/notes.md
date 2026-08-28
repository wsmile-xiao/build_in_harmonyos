# structopt 0.1.3 适配笔记

## 编译环境
- **类型**: header-only C++17（无库编译）
- **编译日期**: 2026-08-28
- **编译器**: clang 15（OHOS 6.0 交叉工具链）
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built

## 编译步骤（conan create 全流程）

```bash
conan create archives/s/structopt/0.1.3 --build=missing
```

### 1. 源码获取（source()）
`get()` 下载 GitHub v0.1.3 tag tarball（212KB），`strip_root=True` 解压。

### 2. 打包（package()）
header-only——拷贝 `include/structopt/` 头文件目录（app/parser/exception 等）到 include。

### 3. 上游测试（build() 集成——rule 4 实测回填）
doctest 单元测试（tests/ 目录——**自带 doctest.hpp，无需网络下载**；54 个
test cases / 393 assertions）——`STRUCTOPT_TESTS=ON` 单独构建：
```bash
cmake <src> -DSTRUCTOPT_TESTS=ON -DSTRUCTOPT_SAMPLES=OFF \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++ \
  -DCMAKE_CXX_FLAGS='-std=c++17'
cmake --build <bdir> -j4
# structopt 测试未注册为 ctest 用例（'No tests were found' 实测——与
# argparse 同源）——直接运行 structopt_tests 可执行（doctest 自带统计）
./build-tests/tests/structopt_tests
```
- aarch64 OHOS 直接可编译（header-only 无平台限制）
- subprocess 调 cmake 用绝对路径（OHOS posix_spawn 不按 PATH 搜索相对名——
  与 rich/vc 同源教训）

**实测结果：54 passed / 0 failed / 0 skipped（54 用例 = 100%，分母=全部用例）**

关键处理（缺依赖就装上 / 环境差异修复）：
1. **直接运行 structopt_tests 二进制**：structopt 的 tests/CMakeLists.txt 未用
   add_test 注册 ctest 用例（'No tests were found' 实测——与 argparse 同源）
   ——改为直接运行 `build-tests/tests/structopt_tests`（doctest 自带统计输出）

## 验证结果
- **构建**: `structopt/0.1.3: Package created`
- **上游测试**: 实测 **54/54 通过（100%）**——54 passed / 0 failed / 0 skipped（393 assertions 全过）——build() 集成回填（rule 4，分母=全部用例）
- **R34 消费者验证**: test_package——头文件存在 + structopt::app 解析 smoke（1/1 = 100%）
