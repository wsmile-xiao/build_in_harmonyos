# inipp 1.0.13 适配笔记

## 编译环境
- **类型**: header-only C++11（无库编译）
- **编译日期**: 2026-08-28
- **编译器**: clang 15（OHOS 6.0 交叉工具链）
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built

## 编译步骤（conan create 全流程）

```bash
conan create archives/i/inipp/1.0.13 --build=missing
```

### 1. 源码获取（source()）
`get()` 下载 GitHub 1.0.13 tag tarball（13KB），`strip_root=True` 解压。

### 2. 打包（package()）
header-only——拷贝 `inipp/inipp.h`（单头文件）到 include。

### 3. 上游测试（build() 集成——rule 4 实测回填）
unittest/（headertest + unittest 二进制 + test*.ini/test*.output 样本——
CMake 自动拷贝到 build 目录；2 个 ctest 用例）——`BUILD_TESTING=ON` 单独
构建 + ctest 运行：
```bash
cmake <src> -DBUILD_TESTING=ON \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++ \
  -DCMAKE_CXX_FLAGS='-std=c++11'
cmake --build <bdir> -j4
ctest --test-dir <bdir>
```
- aarch64 OHOS 直接可编译（header-only 无平台限制）
- subprocess 调 cmake/ctest 用绝对路径（OHOS posix_spawn 不按 PATH 搜索
  相对名——与 rich/vc 同源教训）

**实测结果：18 passed / 0 failed / 0 skipped（18 用例 = 100%，分母=全部用例）**
——unittest 二进制内含 17 个 TEST_METHOD + headertest 编译测试（2 个 ctest
用例实际执行 18 个上游用例，全部通过 exit=0）

## 验证结果
- **构建**: `inipp/1.0.13: Package created`
- **上游测试**: 实测 **18/18 通过（100%）**——build() 集成回填（rule 4，分母=全部 18 用例；unittest 17 个 TEST_METHOD + headertest 编译测试全过）
- **R34 消费者验证**: test_package——头文件存在 + Ini 解析 smoke（1/1 = 100%）
