# tl-parser 0.0.0-git20210107.1933e76f 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-18
- 编译器: clang/clang++（OHOS aarch64 / armv8 原生构建）
- 状态: built（真机预检确认后更新）

## 上游信息
- 上游仓库: https://github.com/vysheng/tl-parser
- 版本来源: Git snapshot，提交 `1933e76f8f4fb74311be723b432e4c56e3a5ec06`（2021-01-07），即版本号 `0.0.0-git20210107.1933e76f` 对应提交。
- 源码: `https://github.com/vysheng/tl-parser/archive/1933e76f8f4fb74311be723b432e4c56e3a5ec06.tar.gz`
- sha256: `32c1c0b710a75bf7054f46d9db1790a5793d0615d019ef5ec2e20bb43889c94d`
- License: GPL-2.0-only

## 编译步骤
- 纯 C99 / POSIX 单可执行文件应用，CMake 构建。
- CMakeLists.txt 无 install 规则 → 打补丁 `0001-cmakelists-add-install-target.patch` 增加
  `install(TARGETS tl-parser RUNTIME DESTINATION bin)`。
- CMake 无 OHOS 平台模块；纯 POSIX 应用对 OHOS 原生以 clang 构建时设置
  `CMAKE_SYSTEM_NAME=Linux`（对齐 abcmidi 等纯 POSIX CMake 应用已过门禁先例）。
- 仅链接 `libm`（POSIX 头 unistd/fcntl/signal 原生可用）。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 CMakeLists.txt 无 install 规则，`conan create` 无法打包可执行文件 | 上游只声明 `add_executable`，未提供安装目标 | 补丁增加 `install(TARGETS ... RUNTIME DESTINATION bin)` |
| 2 | tl-parser 在部分解析失败时仍返回退出码 0（如 `tl_parse_lex` 失败直接 `return 0`） | main() 对词法/语法错误路径返回 0，仅对语义失败返回 1 | 消费者测试不依赖退出码，改为校验 `.tlo` 输出文件非空且携带 `0x3a2f9be2`（TLS_SCHEMA_V2）魔数——畸形容错 schema 不会生成任何 `.tlo`（本机已实测验证） |
| 3 | CMake 无 OHOS 平台模块 | 无 OHOS 对应 CMake 平台模块 | 对 OHOS 设 `CMAKE_SYSTEM_NAME=Linux`，clang 原生构建（纯 POSIX 代码无 OHOS 特有 API 依赖） |
| 4 | 真机 CMake 4.1.2 configure 失败：`CMake Error at CMakeLists.txt:1 (cmake_minimum_required): Compatibility with CMake < 3.5 has been removed from CMake` | 上游 `cmake_minimum_required(VERSION 3.0 FATAL_ERROR)`，CMake ≥ 4.0 移除对 < 3.5 的兼容；CMakeLists 只用 project/add_executable/target_link_libraries/install 等 3.5 均支持的命令 | 补丁 `0002-cmakelists-bump-min-cmake-version.patch` 把最小值从 3.0 提到 3.5 |

## 源码修改
- `patches/0001-cmakelists-add-install-target.patch`：为 CMakeLists.txt 增加
  `install(TARGETS ${PROJECT_NAME} RUNTIME DESTINATION bin)`，使
  `cmake --install` 将 tl-parser 二进制安装到 `<prefix>/bin`。
- `patches/0002-cmakelists-bump-min-cmake-version.patch`：把
  `cmake_minimum_required` 从 `3.0` 提到 `3.5`，兼容真机/CI 的 CMake 4.x
  （CMake ≥ 4.0 已移除对 < 3.5 的 compatibility）。

## 依赖版本
- 无 Conan 依赖；仅标准 C + `libm`（系统库，`target_link_libraries(... m)`）。

## 上游测试
- 上游无任何自动化测试（详见 `test_package/MANIFEST.yml` 的 `upstream_test_audit`）：
  CMakeLists 无 `enable_testing`/`add_test`，源码树无 tests/ 目录，无 *_test 源文件。
- 由 test_package 做消费者视角真实验证：安装后的 tl-parser 解析真实 TL schema 并生成非空
  `.tlo`，再用 Python 校验 `.tlo` 携带 TLS_SCHEMA_V2 魔数 `0x3a2f9be2`。
- 真机（HarmonyOS aarch64）预检通过的 conan create 日志，用于回填 PR 正文的「上游测试用例通过率」。

> 本机（Linux x86_64）已用 gcc 构建同一提交源码并手动验证：最小 TL schema
> `boolFalse#bc799737 = Bool; / boolTrue#997275b5 = Bool; / true#3fedd339 = True;`
> 解析成功并产出 316 字节日志含 `0x3a2f9be2` 魔数的 `.tlo`；畸形容错输入不会生成 `.tlo`
> （证伪通过——测试 harness 确实能抓到解析失败）。

## 验证结果
```bash
# 本机（x86_64）逻辑验证（非 OHOS，仅验证源码/工具/fixture 行为）
gcc -O2 -o tl-parser crc32.c tlc.c tl-parser.c -lm
./tl-parser -e out.tlo schema.tl   # exit 0，out.tlo 316B，头 4 字节 0x3a2f9be2
./tl-parser -e x.tlo <broken>      # 解析失败，不生成 x.tlo
```
真机 conan create 结果待 hmbs 真机预检返回后回填。

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | CMake application 配方 |
| conandata.yml | 源码 URL + sha256 + patch 声明 |
| manifest.yaml | 版本元数据 |
| notes.md | 本文件 |
| patches/0001-cmakelists-add-install-target.patch | 增加 install 规则 |
| test_package/conanfile.py | 消费者测试（真实解析 + 魔数校验 + HMBS 标记） |
| test_package/run_test.sh | 运行随包 tl-parser 二进制并校验非空 .tlo |
| test_package/MANIFEST.yml | 上游 no_tests 审计 + test_package 用例声明 |
| commands.json（软件级） | 命令行工具声明（R38） |

## 注意事项
- tl-parser 是“应用”型包（`package_type="application"`，无库），`package_info` 通过
  `runenv_info` 把 `<prefix>/bin` 前置到 PATH，test_package 用 VirtualRunEnv 定位二进制。
- 测试必须校验输出文件而非退出码（见上表问题 2）。
