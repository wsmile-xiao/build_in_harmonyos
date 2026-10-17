# E543 — 上游 CMakeLists 硬编码 RUN_CONAN 导致 configure 失败的 header-only 库应绕过上游 CMake 走 header-library 配方

## 错误特征

```
CMake Error at cmake/Conan.cmake:10 (CONAN_CMAKE_RUN):
  Unknown CMake command "CONAN_CMAKE_RUN".
-- Downloading conan.cmake from https://github.com/conan-io/cmake-conan
```

configure 阶段即失败；失败根源不在库本身，而在上游 CMakeLists 无条件调用
`INCLUDE(cmake/Conan.cmake)` + `RUN_CONAN()`（cmake-conan 集成）：先下载
conan.cmake（受限网络下为 0 字节空文件），再 `CONAN_CMAKE_RUN(REQUIRES ...
catch2/3.2.1 ...)`——该测试依赖固定版本在私有 registry 不可得时同样失败。

## 触发条件

- 构建系统: cmake（上游 CMakeLists.txt 硬编码 cmake-conan 集成）
- 阶段: configure
- 库形态: header-only（无编译产物）；若同时存在 install/export 的 INTERFACE 库参见 E322

## 根因分析

上游模板化工程（cmake-conan 集成、Catch2 测试）把依赖获取绑定在 configure 期：
1. `file(DOWNLOAD conan.cmake ...)` 在受限网络环境下载失败（0 字节/空文件），
   后续 `include()` 得到空文件 → `CONAN_CMAKE_RUN` 未定义 → configure 失败；
2. 即使下载成功，`REQUIRES catch2/3.2.1` 若在私有 registry（ohpcd）中无该精确版本，
   conan 解析失败；
3. 对 header-only 库而言，上游 CMake 只承担"打包头文件 + 跑测试"两件事，
   没有必须保留的编译产物，绕过整套 CMake 构建是零损失的适配路径。

## 解决方案

### 推荐方案

header-only-bypass-upstream-cmake：

- manifest.yaml `build_system: custom`（不走上游 cmake configure/make）；
- conanfile.py 用 `package_type = "header-library"`，`package()` 仅拷贝
  `include/crc_cpp.h` 与 LICENSE；`build()` 只做 `apply_conandata_patches`；
- 上游 Catch2 测试不进配方依赖：用 registry 可用版本（如 catch2/3.8.1 替代
  固定 catch2/3.2.1）的头文件 + libCatch2Main 直接 `clang++ -std=c++20` 编译
  `test/test.cpp` 并运行，结果如实记录（本例 2/2 test cases、47 assertions 通过）；
- 参照先例：archives/c/crc_cpp/1.2.0（本库）、archives/c/clipp/1.2.3（单头文件）。

### 禁止做法

- ❌ 强行 patch 上游 cmake/Conan.cmake 或伪造 conan.cmake 下载（除非库非纯
  header-only 且必须走上游 CMake，才考虑 fallback patch 去掉 RUN_CONAN）；
- ❌ 把 catch2 等测试依赖写进配方 `requires`（使 package_id 依赖测试框架）；
- ❌ 把 0 字节 conan.cmake / 配置失败写成"外部阻塞"跳过——header-only 库
  绕过上游 CMake 是本任务的正确适配动作。

## 验证

```bash
conan create archives/c/crc_cpp/1.2.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# → exit 0，test_package 两个消费者二进制 ALL PASS
clang++ -std=c++20 -I include -I <catch2-3.8.1>/include test/test.cpp \
  <catch2-3.8.1>/lib/libCatch2Main.a <catch2-3.8.1>/lib/libCatch2.a -o tests && ./tests
# → All tests passed (47 assertions in 2 test cases)
```

## 关联条目

- 相关: E257（header-only 无构建系统库配方 G1 build() 门禁）、
  E321（header-only lite 类库 conan1→2 迁移）、
  E322（header-only CMake INTERFACE 库且上游自带 install/export 的配方，
  仍走上游 cmake）