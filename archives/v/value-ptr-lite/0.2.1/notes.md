# value-ptr-lite 0.2.1 适配笔记

## 编译环境
- 构建系统: cmake（header-only 接口库）
- 编译日期: 2026-09-02
- 编译器: clang 15 / clang++ (aarch64-linux-ohos, OHOS 6.0)
- 状态: published
- 上游: https://github.com/nonstd-lite/value-ptr-lite (tag v0.2.1)
- 官方 tarball SHA-256: 683a6d98512249c4899d70ee1c3005843e1b05988c51f332fc0ad23cff9585f0

## 编译步骤

1. init-build: 官方 tag tarball 下载、解压至 .orig/.work，环境核验通过。
2. lang-preflight: 判定 cpp（build_system=cmake, source_stats=cpp 主体）→ 匹配，进入适配主流程。
3. 上游测试编译（OHOS clang15，-std=c++98/11/14/17 四变体）:
   `cmake .. -DCMAKE_CXX_COMPILER=clang++ -DCMAKE_CXX_STANDARD=17 -DVALUE_PTR_LITE_OPT_BUILD_TESTS=ON`
   `cmake --build .` → 生成 value_ptr-lite-cpp98/11/14/17.t，全部构建成功。
4. 上游测试运行: 四个变体 `./value_ptr-lite-cppXX.t --pass` 全部 51 个独立用例通过；
   `--pass "*"` 全量 58 个（含 6 隐藏诊断 + 1 [.applet] 空占位）通过。
5. conan-init 生成配方骨架 → 因上游是 header-only CMake 库，重写为 header-library 配方:
   - package_type=header-library，source() 官方 URL + SHA-256；
   - generate() 关闭上游测试/示例，BUILD_SHARED_LIBS=OFF；
   - package() 复用上游 cmake.install()（自带 install() 导出 config）；
   - package_info() 无 libs，暴露 value-ptr-lite::value-ptr-lite target。
6. test_package: 消费者 test_package.cpp 真实调用 value_ptr 构造/复制/访问/比较 API，
   test() 直接运行二进制（R34 实质验证）。conan create 中输出 "consumer test: ALL OK"。
7. conan-verify: G0-G4 全 PASS（G0 命中 E092 cmake-ohos 提示，G2 conan create 实际通过，
   不构成阻塞）；报告 reports/conan-verify-report.md。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 按 autotools 生成配方模板 | 构建系统检测默认值 | 按真实 CMake header-only 结构重写 conanfile.py（package_type=header-library + CMakeToolchain） |
| 2 | conan-init 生成的 test_package 为 C 空壳 | 通用模板 | 替换为 C++ 消费者测试，真实调用被测包 API（R34） |
| 3 | CMake 平台识别警告（HarmonyOS） | CMake 无 HarmonyOS platform module（E092） | OHOS 适配版 conan 的 CMakeToolchain 已注入 CMAKE_SYSTEM_NAME 映射，conan create 实际成功，无需处理 |

## 源码修改

无（header-only，零补丁，patches=0）。仅修正 Conan 配方、test_package 与 manifest/notes。

## 上游测试台账

- 用户测试源: test/value_ptr.t.cpp（52 个 CASE，含 1 个 [.applet] 空占位）、test/value_ptr-main.t.cpp（6 个隐藏诊断 CASE）。
- 框架头: test/lest_cpp03.hpp（lest 单头文件框架，非独立用例）。
- 独立可运行用例: 51 个（value_ptr.t.cpp），cpp98/11/14/17 四变体全量通过 = 51/51。
- 隐藏诊断用例: 6 个（main 文件 [.value-ptr][.version] 等），--pass "*" 全量通过。
- 空占位: "value_ptr: xxx" [.applet]（无断言，不计独立用例）。
- 样例: example/01-pimpl.cpp / 02-tree.cpp / 03-no-exceptions.cpp（编译验证用，非独立用例）。
- 统计口径: 全目录发现 58 个 CASE；独立上游用例 51 个全通过 = 100%（51/51），
  隐藏诊断 6/6 通过，全量 58/58 通过。构建目标: value_ptr-lite-cpp98/11/14/17.t。
---

**编译结束**: 2026-09-02 23:13
**最终状态**: published
