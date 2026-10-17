# cli11 2.7.2 适配笔记

## 编译环境
- **类型**: header-only C++11（无库编译）
- **编译日期**: 2026-08-28
- **编译器**: clang 15（OHOS 6.0 交叉工具链）
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built

## 编译步骤（conan create 全流程）

```bash
conan create archives/c/cli11/2.7.2 --build=missing
```

### 1. 源码获取（source()）
`get()` 下载 GitHub v2.7.2 tag tarball（1.4MB），`strip_root=True` 解压。

### 2. 打包（package()）
header-only——`shutil.copytree` 拷贝 `include/CLI/` 头文件（CLI.hpp 伞头 +
App/Option/Config/Error 等）到 include。

### 3. 上游测试（build() 集成——rule 4 实测回填）
Catch2 单元测试（tests/*.cpp，24 个 ctest 用例）——`CLI11_BUILD_TESTS=ON` 单独
构建 + ctest 运行：
```bash
cmake <src> -DCLI11_BUILD_TESTS=ON -DCLI11_BUILD_EXAMPLES=OFF \
  -DCLI11_BUILD_DOCS=OFF \
  -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++ \
  -DCMAKE_CXX_FLAGS='-std=c++14'
cmake --build <bdir> -j4
ctest --test-dir <bdir>
```
- aarch64 OHOS 直接可编译（header-only 无平台限制）
- subprocess 调 cmake/ctest 用绝对路径（OHOS posix_spawn 不按 PATH 搜索
  相对名——与 rich/vc 同源教训）

**实测结果：24 passed / 0 failed / 0 skipped（24 用例 = 100%，分母=全部用例）**

关键处理（缺依赖就装上）：
1. **Catch2 依赖**：CMake 默认从 GitHub 下载 catch.hpp（超时实测）——
   `requires catch2/2.13.10-r0`（ohpcd 已发布，hash 3725c0f0 与 CLI11 期望
   完全一致）——build() 从 conan 包拷贝 catch.hpp 到 CMake 缓存位置
   （`build-tests/tests/catch2/catch.hpp`）→ 走缓存分支不再下载
2. **pthread_testcancel**：OHOS libc 缺失（AppTest.cpp:3162 编译失败实测——
   与 commoncpp2 同源）——写 stub 头 + `-include` 注入测试编译参数

## 验证结果
- **构建**: `cli11/2.7.2: Package created`
- **上游测试**: 实测 **24/24 通过（100%）**——build() 集成回填（rule 4，分母=全部用例）
- **R34 消费者验证**: test_package——头文件存在 + CLI::App 解析 smoke（1/1 = 100%）
