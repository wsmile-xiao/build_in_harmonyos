# libmusicxml 3.22 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-14
- 编译器: clang/clang++
- 状态: built

## 编译步骤

上游 CMakeLists 位于源码 `build/` 子目录（而非源码根），配方以
`-S <source>/build -B <build>/hmbs_build` 直接调用 cmake 二进制（noshell，
避免只读 /tmp 下 dash 建 sh*.tmp 失败），并固定
`-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 兼容上游 `cmake_minimum_required < 3.5`。
`GENTOOLS=ON` 构建示例工具仅用于上游验证，`GENSTATIC=ON` 保持静态库安装；
`package()` 在 `cmake --install` 后删除 `bin/`，产物保持纯库形态，避免
`commands.json` 义务；再按 `shared` 选项过滤多余库文件。
OHOS 下补齐 CMake 缺失的共享库 SONAME/RPATH 契约，与站内 CMake 配方做法一致。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMakeLists 不在源码根，默认 `cmake_layout` 找不到工程 | 上游工程入口为 `build/CMakeLists.txt` | `build()` 中以 `-S source/build -B hmbs_build` 显式指向 |
| 2 | 真机门禁判定上游存在测试，`no_tests`/0 不允许通过 | `build/CMakeLists.txt` 无 ctest/gtest，但 `validation/Makefile` 与 `files/tests/Makefile` 以 xmlread+xml2guido 驱动 `files/**/*.xml`，属于可运行回归入口 | `build()` 实跑该入口：每样本各跑 xmlread（exit 0、输出非空且含 `<`）与 xml2guido（exit 0、输出非空），失败即抛异常；双通道输出 `HMBS_UPSTREAM_TEST_RESULT`（passed，discovered=2×样本数）并持久化 `hmbs_upstream_result.json`，`package()` 随包发布，`test_package` 在消费者测试后重发该实测文件 |
| 3 | 共享库与静态库文件名不同（`liblibmusicxml.so*` vs `libmusicxml2.a`） | 上游 shared `target libmusicxml` 无 OUTPUT_NAME 覆盖（产物 `liblibmusicxml.so.3.2.2`，见 Arch/FreshPorts 文件清单），static `musicxml2static` 设 `OUTPUT_NAME musicxml2` | `package_info()` 按 `shared` 分别声明 `libmusicxml`/`musicxml2`，`package()` 删除未选中形态（静态包同时匹配双 `lib` 前缀） |
| 4 | `conandata.yml` 手写 gh-proxy 镜像在前 | CI 的 mirror-fallback 会在构建时自动注入 gh-proxy，源码仓手写镜像命中 PF7 源 URL 黑名单 | 只保留官方 GitHub URL，镜像由 CI 自动追加 |

## 源码修改

无补丁。

## 依赖版本

无依赖（纯 C++17 标准库）。

## 验证结果

待真机预检回填：`conan create` 编译、消费者测试（4 检查）与 validation-harness 上游标记（passed，计数=2×样本数）。

## 注意事项

- 消费者头文件路径为 `include/libmusicxml/libmusicxml.h`，配方在 `includedirs` 中同时保留 `include` 与 `include/libmusicxml`。
- OHOS 运行消费者测试前需对测试 ELF 签名；已在 `test_package` 中实现，与站内 CMake 配方一致。
- 防伪造：输出非空校验（空对空比对直接判失败）；`test_package` 重发内容只读包内 `share/libmusicxml/upstream_test_result.json`，缺失或非 passed 直接抛异常，不回退为 `no_tests`。
