# clucene 2.3.3.4 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-08
- 编译器: clang/clang++ 15 (OHOS SDK)
- 状态: built

## 编译步骤

1. 下载源码：https://downloads.sourceforge.net/clucene/clucene-core-2.3.3.4.tar.gz
2. 解压到 build 目录
3. 应用补丁：patches/0001-cmake-minimum-version.patch (2.4→3.5)
4. cmake 配置：
   ```bash
   cmake -DCMAKE_BUILD_TYPE=Release \
         -DBUILD_SHARED_LIBS=OFF \
         -DBUILD_STATIC_LIBRARIES=ON \
         -DBUILD_CONTRIBS=OFF \
         -DBUILD_CONTRIBS_LIB=OFF \
         -DENABLE_ANSI_MODE=OFF \
         -DENABLE_COMPILE_TESTS=OFF \
         -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
         -B build -S .
   ```
5. 编译：cmake --build build -j1
6. 构建上游测试：cmake --build build --target cl_test
7. 签名并运行：binary-sign-tool sign -inFile build/bin/cl_test -outFile build/bin/cl_test.signed -selfSign 1 && ctest --test-dir build --output-on-failure
8. 安装：cmake --install build --prefix /

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake Error: compatibility with CMake < 3.5 | 上游 requires 2.4, OHOS cmake 较新需 policy 3.5 | 补丁提升 minimum 至 3.5，并加 -DCMAKE_POLICY_VERSION_MINIMUM=3.5 |
| 2 | ENABLE_ANSI_MODE 添加 -ansi 导致 clang 警告 | GNUCXX 模式自动加 -ansi | 显式 -DENABLE_ANSI_MODE=OFF |
| 3 | cl_test 为 EXCLUDE_FROM_ALL，ctest 默认不构建 | 上游设计 | build() 中显式 cmake.build(target="cl_test") |
| 4 | OHOS 执行测试需签名 | OHOS 安全机制 | build() 中调用 binary-sign-tool 签名 |
| 5 | 源码字符集函数探测在 OHOS bionic 上部分缺失 | Musl/bionic 差异 | 复用上游 CheckFunction 探测，自动回退到 internal char functions (LUCENE_USE_INTERNAL_CHAR_FUNCTIONS=ON 默认) |

## 源码修改

- patches/0001-cmake-minimum-version.patch
  - CMakeLists.txt: CMAKE_MINIMUM_REQUIRED 2.4.0 → 3.5

## 依赖版本

无外部依赖（zlib 可选，未启用；Boost 仅用于文档，可选）

## 验证结果

本地 x86_64 验证（OHOS 真机待 hmbs 预检）:
```bash
# 检出后本地模拟（需 OHOS 真机完整验证）
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 日志应含：Found upstream test binary: .../bin/cl_test 且 ctest 输出 100% passed
ls /usr/local/lib/libclucene*
# libclucene-core.a, libclucene-shared.a, libclucene-core.so.1 等
```

## 交付物

| 文件 | 说明 |
|------|------|
| libclucene-core.so / .a | 核心检索库 |
| libclucene-shared.so / .a | 共享工具库 |
| include/CLucene/ | 头文件 |
| lib/pkgconfig/libclucene-core.pc | pkg-config |
| lib/CLuceneConfig.cmake | CMake 包配置 |

## 注意事项

- contrib 库默认关闭，若需高亮/雪球分词可开启 BUILD_CONTRIBS_LIB=ON 并应用 blfs patch
- 动态库版本 SOVERSION=1，符合上游
- Patches 均不含 __OHOS__ 宏（R8）
