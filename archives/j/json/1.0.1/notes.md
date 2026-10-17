# json 1.0.1 适配笔记

## 编译环境
- 构建系统: header-only（无 configure/cmake/make；单头文件 C99 库）
- 编译日期: 2026-09-23
- 编译器: clang 15.0.4（OHOS 工具链）
- 状态: built

## 上游来源
- 官方仓库: https://github.com/mjansson/json（tag 1.0.1）
- 源码: json.h（单头文件，C99，Public Domain）
- tarball SHA-256: 5d8b5419e47b5c8c8a49bb3aa2b82f14029cadf1c441e1408a8387d80c3e1f99

## 编译步骤
header-only 库无构建系统，无 configure/make/install 步骤。适配内容为：
1. 核验单头文件 json.h 可被 C99 编译（上游自带最小测试模式 JSON_TEST）
2. Conan header-only 配方打包头文件至 include/
3. test_package 消费者：include json.h 并调用公开 API 解析 JSON，验证编译/链接/运行

## 上游测试全量枚举台账（R51 三步法）

上游唯一测试源：json.h 内 `#ifdef JSON_TEST` 块（第 714-847 行），即 README 所述的
"minimal test case"（编译命令 `clang -D JSON_TEST -x c --std=c99 json.h`）。

| # | 测试声明/入口 | 分类 | 是否独立上游用例 | 实际运行 | 结果 |
|---|--------------|------|-----------------|---------|------|
| 1 | JSON_TEST main 中标准 JSON parse 场景（json_parse，19 个 VERIFY_TOKEN 断言） | 用户测试源（唯一主测试函数内场景 1） | 是 | 是 | PASS |
| 2 | JSON_TEST main 中 SJSON parse 场景（sjson_parse，19 个 VERIFY_TOKEN 断言） | 用户测试源（唯一主测试函数内场景 2） | 是 | 是 | PASS |
| - | VERIFY_TOKEN / VERIFY_TOKEN_ID / VERIFY_TOKEN_ID_VALUE 宏 | 框架内部断言宏，非用户用例 | 否 | - | - |

统计口径（双口径）：
- source_declared_total: 2（JSON_TEST 块内 2 个独立解析场景）
- configured_executable_total: 2（同一最小测试程序内两场景均被实例化执行）
- executed_passed_total: 2（输出 "Minimal tests passed"，exit 0）
- 通过率: 2/2 (100.0%)

运行证据：
```bash
cd <work>/json-1.0.1.work
clang -D JSON_TEST -x c --std=c99 json.h -o json_selftest   # COMPILE_EXIT:0（仅 -Wformat 警告）
./json_selftest                                            # 输出 Minimal tests passed, RUN_EXIT:0
```
日志: /storage/Users/currentUser/tmp/logs/json-1.0.1/upstream_selftest_compile.log
SHA-256: 52b50bf50da25f0c9b4f03b047f788a5587442ad06e221cb0a44ad88aeba545e

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | lang-preflight 判 json 为 other（env_unsupported 误报） | 工具源码统计只认 .c/.cpp 实源，header-only 库无实源文件 | 以上游自带 JSON_TEST 编译+运行实证 C99 语言身份（COMPILE_EXIT:0/RUN_EXIT:0），按 c/cpp 兼容族继续适配 |
| 2 | init-build 直连 github 下载失败 | 本机 github.com 直连超时 | 经 gh-proxy 镜像下载官方 tag tarball 并核验 SHA-256 |

## 源码修改
无（header-only，无补丁）

## 依赖版本
无第三方依赖

## 验证结果
见上方上游测试台账：2/2 (100.0%) 通过。

## 鸿蒙专项测试

test_package/test.c（消费者用例，OHOS profile 实测）：仅通过公开头文件 json.h 调用公开 API：
- json_parse：解析标准 JSON `{"name":"json","version":1}`，断言 token 数与类型（JSON_OBJECT/JSON_STRING）
- sjson_parse：解析 SJSON `name = json\nversion = 1`，断言根 token 类型
- 输出可观察结果 "parsed N JSON tokens, M SJSON tokens" 并返回 0

已在 OHOS profile（clang 15, armv8）下经 conan create 编译、链接、运行通过：
```
clang-15-armv8-17-release
Building C object CMakeFiles/test_json.dir/test.c.obj
Linking C executable test_json
1/1 Test #1: test_json ........................   Passed    0.02 sec
100% tests passed, 0 tests failed out of 1
```
日志: archives/j/json/1.0.1/reports/conan-create.log（conan-verify G2 产物）

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | header-only 配方 |
| conandata.yml | 官方源 + SHA-256 |
| test_package/ | 消费者验证 |

## 注意事项
- 库为纯头文件（json.h），安装后只提供 include 头文件，无二进制产物 → 不需要 commands.json（R38 仅 tool 类型）
---

**编译结束**: 2026-09-27 20:45
**最终状态**: built
