# platform_folders 4.2.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-03
- 编译器: clang/clang++ (aarch64-linux-ohos, clang 15.0.4)
- 状态: built

## 编译步骤

platform_folders 为特殊目录查询库，零第三方依赖（W0 依赖预检通过）。

1. 官方源码：https://github.com/sago007/PlatformFolders/archive/refs/tags/4.2.0.tar.gz
   - sha256=31bb0f64a27315aec8994f226332aaafe9888d00bb69a2ff2dff9912e2f4ccf4
   - codeload 与 github.com 两路拉取 sha256 一致（官方包确定性校验通过）。
2. Conan 配方：`conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=同`。
   - CMakeToolchain generic_system 块：OHOS → cmake_system_name=OHOS、
     cmake_system_processor=aarch64（与本仓 gcem 配方一致）。
   - 上游 `cmake_minimum_required(VERSION 3.1.0)`，CMake 4 要求 >=3.5，
     generate() 注入 `CMAKE_POLICY_VERSION_MINIMUM=3.5`。
   - `PLATFORMFOLDERS_BUILD_TESTING=ON`：test/CMakeLists.txt 的 `_def_test`
     宏注册 16 个 ctest 用例，build() 内 `cmake.test()` 直接跑全量上游测试。
   - 静态库（BUILD_SHARED_LIBS=OFF 默认），无系统同名库冲突。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 本机 GitHub 直连下载超时 (curl exit 28) | 网络限制 | codeload/github.com 重试直连，均 42KB 包，sha256 一致 |
| 2 | 上游测试运行依赖真实 HOME | 测试仅断言返回目录串非空 | OHOS CI worker 以 currentUser 运行（conan 缓存位于 /storage/Users/currentUser/），HOME 存在，16 用例确定性通过 |

## 源码修改

无（零补丁）。

## 依赖版本

无外部依赖。

## 验证结果

- 上游官方测试：16 个 ctest 用例全部通过（getConfigHome/getDataHome/getCacheDir/
  getStateDir/getDesktopFolder/getDocumentsFolder/getDownloadFolder1/getMusicFolder/
  getPicturesFolder/getPublicFolder/getSaveGamesFolder1/getVideoFolder/
  appendAdditionalConfigDirectories/appendAdditionalDataDirectories/integration/
  internalTest）。integration 覆盖类方法（PlatformFolders）与 20+ 目录 getter；
  internalTest 为 sago::internal::appendExtraFoldersTokenizer 纯逻辑断言。
- 消费者测试（test_package/test_platform_folders.cpp）：20 checks ALL OK，
  链接 libplatform_folders 真实调用公开 API + internal 分词器。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 编译库配方（含层1 cmake.test()） |
| conandata.yml | 官方源 + sha256 |
| manifest.yaml | 版本级 manifest（built） |
| test_package/test_platform_folders.cpp | 消费者 API 测试 |
| test_package/MANIFEST.yml | 上游测试声明（16 用例） |

## 注意事项

- OHOS 属非 Windows/非 Apple 平台 → 走 Linux/XDG 实现分支（读 HOME 与 XDG_*
  环境变量、$XDG_CONFIG_HOME/user-dirs.dirs）。非 root 用户返回路径即非空，
  测试不要求目录真实存在。
- 库类型无 bin/ 可执行产物 → 无 commands.json 需求（R38 不涉及）。

---
**最终状态**: built
