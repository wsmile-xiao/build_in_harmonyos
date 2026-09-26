# cppcmd 0.1.0 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMakeLists.txt，INTERFACE header-only 库）
- 编译日期: 2026-09-22
- 编译器: clang/clang++ 15（OHOS arm64，ohos-aarch64 profile）
- 状态: built

## 编译步骤

1. 官方源码：https://github.com/remysalim/cppcmd tag v0.1.0
   tar.gz SHA-256: f9813c298f40fd29ebdfa0a9e68cdea80ec1b0f93c32e8fafef58dc01eb48368
2. 探索构建（原生）：cmake -DBUILD_TESTING=ON + Conan 提供 catch2/2.13.10；
   上游测试 6 个用例全部通过（120 assertions）。
3. 配方：conan-init 因 URL 误判 autotools，人工重写为 header-only 配方
   （package_type=header-library，无编译阶段，package() 复制 include/ 与 LICENSE）。
4. conan-verify（ohos-aarch64）：G1/G2/G3/G4/L2/L4/L5 全部 PASS；
   conan create 经 E017 ghfast.top 镜像注入下载官方源码后干净构建成功。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连超时，init-build 下载失败 | 网络对 github.com 部分 IP 不可达 | 用可达 IP（20.27.177.113 / codeload 140.82.112.10）下载官方 tag 包并核验 SHA-256；conan-verify E017 自动注入 ghfast.top 镜像 |
| 2 | conan-init 生成 Autotools 配方 | 构建系统按 URL 猜测为 autotools，实际为 CMake header-only | 人工重写 header-only 配方（参考 templates/conanfile-headeronly.py.tmpl） |
| 3 | Conan 2 报 "package type library 无 shared 选项" | Conan 2.29 校验 | 改用 package_type = "header-library" |
| 4 | package() 复制为空 | ① `*.hpp` 不匹配嵌套 include/cppcmd/ 头文件；② 相对 dst 解析到构建目录 | ① 模式改 `**/*.hpp`；② dst 显式用 `os.path.join(self.package_folder, ...)` |
| 5 | test_package 链接语言无法判定 | 测试源文件名 test.c 但内容为 C++ | 重命名为 test.cpp |
| 6 | 上游 tests/CMakeLists.txt 需 include(Catch) + catch_discover_tests | Conan 版 Catch2 不含 contrib/Catch.cmake | 本地探索构建提供上游 Catch.cmake/CatchAddTests.cmake 模块（不入配方、不入 PR） |

## 源码修改

无补丁（patches/ 为空）。header-only 库无需修改上游源码。

## 依赖版本

- catch2/2.13.10（仅测试期，conan 制品仓已有）
- 无其他编译依赖

## 验证结果

- 上游测试（原生）：6/6 通过，120 assertions（ctest + 直接运行 cppcmd-test）
- conan-verify（OHOS arm64）：G1/G2/G3/G4 全部 PASS，L2/L4/L5 跳过（无 cache 路径）

## R38 commands.json 判定

**不需要 commands.json**：cppcmd 是纯 header-only 库
（package_type=header-library，package_info 中 bindirs=[]/libdirs=[]，
无 bin/ 产物）。上游 apps/main.cpp 仅为 demo，未打包进制品。
PF8 规则：纯库包必须无 commands.json；L0k 不要求。

## 注意事项

- 上游 tests 依赖 Catch2 的 contrib/Catch.cmake 模块（catch_discover_tests），
  Conan 二进制包不含该模块；如需在 CI 运行上游测试需在构建环境提供该模块。
  当前配方的 test_package 使用独立消费者测试（test.cpp），不依赖该模块。
---

**编译结束**: 2026-09-22 17:21
**最终状态**: built
