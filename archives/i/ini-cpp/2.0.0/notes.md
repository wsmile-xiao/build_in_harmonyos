# ini-cpp 2.0.0 适配笔记

## 上游信息

- 仓库: https://github.com/SSARCandy/ini-cpp
- 版本: 2.0.0（tag `v2.0.0` = commit 44f49dce68af3e35abf73a7e8762a4ce191848f0，已核验）
- 源码 tarball: https://codeload.github.com/SSARCandy/ini-cpp/tar.gz/refs/tags/v2.0.0
- SHA-256: `5127bb0d2c3a0b7d7adc16afd86507422f5f2f449506e218c29af6ce882ad3b0`
  （codeload 与 github archive 端点 tarball 哈希一致）
- 许可证: MIT（LICENSE.txt）

## 库类型

header-only C++17 INI 解析器：单头文件 `ini/ini.h`（namespace `inih`），
支持 sections/keys、`Get<T>` 类型访问、`GetVector`。无库文件需编译，
`package()` 只安装头文件到 `include/ini/ini.h`。

## 上游测试

- `test/tests.cpp`：27 个 GTest TEST 用例（INIReader/INIWriter 各功能）
- `test/fixtures/`：config.ini、bad_file.ini、bigfile.ini、duplicate_keys.ini
- 依赖 googletest git submodule —— **release tarball 不含 submodule**（googletest/ 为空目录），
  上游 CMake 仅在 Debug 模式 `ADD_SUBDIRECTORY(googletest)`，无法直接复用
- 方案：build() 内用 profile 编译器 clang++ 直接编译 tests.cpp，链接
  ohpcd 已发布的 `gtest/1.17.0`（`test_requires`，不外泄给消费者），
  fixtures 手工复制到运行目录后执行 all_test 二进制，回填真实通过率
- OHOS 沙箱 subprocess 不搜 PATH（posix_spawn 差异）：编译器取
  `tools.build:compiler_executables` conf 绝对路径

## 配方要点

- `package_type = "header-library"`，settings 四件套
- `test_requires("gtest/1.17.0")`：仅测试期依赖，不进入消费者闭包
- `package_info()`：`includedirs = ["include"]`、`libs = []`（header-only）
- test_package：CMake + sample.cpp 编译运行，R34 真实调用
  INIReader（Sections/Keys/Get 类型访问）

## 未决/后续

- 无系统同名库冲突，无需静态化
- 无依赖发布阻塞（gtest/1.17.0 已发布）
---

**编译结束**: 2026-09-23 00:15
**最终状态**: built
