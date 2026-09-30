# openddl-parser 0.5.2 — 适配笔记

## 概述
- 上游：https://github.com/kimkulling/openddl-parser （MIT）
- 用途：OpenDDL / OGEX 解析器（Assimp 的 OpenDDL 解析依赖）
- 构建系统：CMake（`CMakeLists.txt`，`PROJECT( OpenDDL-Parser )`）
- 本版本：官方 tag `v0.5.2`，配方版本 0.5.2

## 构建与验证（本机 HarmonyOS PC, aarch64, musl）
1. `cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=/data/service/hnp/bin/clang -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++ -DCMAKE_INSTALL_PREFIX=<prefix>` → 成功
2. `make -j1`（HMDFS 下 `make -jN` 的 jobserver mkfifo 会报 Operation not permitted，但 make 可自动回退并行成功；本地手动构建建议 `-j1` 规避噪声）→ 成功
3. `./bin/openddlparser_unittest` → **125/125 PASSED**（10 个 gtest 测试类，7ms）
4. `cmake --install .` → 产出 `lib/libopenddlparser.a` + `include/openddlparser/*.h` + cmake config（纯库，无 bin 产物 → 库类型，不需要 commands.json）
5. `conan create ... -pr:h=ci/conan/profiles/ohos-aarch64` → 通过（含 test_package 消费者运行）

## 上游测试台账（双口径）
- 源码声明总数：**125**（test/ 目录 10 个独立 gtest 用户测试源文件，`TEST(`/`TEST_F(` 声明合计 125 个）
  - DDLNodeTest.cpp 12 | OpenDDLCommonTest.cpp 9 | OpenDDLDefectsTest.cpp 10 | OpenDDLExportTest.cpp 10 | OpenDDLIntegrationTest.cpp 5 | OpenDDLParserTest.cpp 36 | OpenDDLParserUtilsTest.cpp 18 | OpenDDLStreamTest.cpp 2 | OssFuzzTest.cpp 3 | ValueTest.cpp 20
- 当前 OHOS 配置实际实例化/执行：**125**（CMakeLists 无条件编译全部测试源进 openddlparser_unittest）
- 实际运行通过：**125/125 (100%)**
- 口径：`125/125 (100.0%)`（全量声明）＝ `125/125 (100.0%)`（当前配置可执行集合）
- 未运行/未实例化：0；跳过：0；不可运行：0

## 消费者验证
- `consumer/consumer_openddl_parser.cpp`：模拟 OGEX 场景加载器，仅用公开头文件/公开 API
  （`OpenDDLParser::parse/getRoot`、`DDLNode::getChildNodeList/getType/getProperties`、
  `Property`/`Value` 公开字段），链 `libopenddlparser.a` 编译运行通过，输出
  `CONSUMER_PASS`。
- `test_package/test_openddl_parser.cpp`：conan create 内置消费者（CTest）通过。

## 鸿蒙专项验证（test_ohos/run_ohos_test.py）
- T1 ELF64 AArch64 ✅ | T2 无 glibc/ld-linux（musl）✅ | T3 签名段（静态库场景不适用）
  | T4 无宿主绝对路径泄漏 ✅ | T5 真实解析验证（链最终静态库）✅
- 全部通过，`OHOS_SPECIAL_PASS`。

## 踩坑与知识候选
1. **上游版本字符串滞后**：v0.5.2 tag 源码 `code/OpenDDLParser.cpp` 中
   `static const char *Version = "0.4.0";`（上游未同步），CMake 读出的 PROJECT_VERSION
   也是 0.4.0；配方/归档版本以官方 tag 为准（0.5.2），`getVersion()` 返回 0.4.0 属上游事实。
   → 候选：跨库可复用（判定包 tag 版本 ≠ 源码内嵌版本号时的处理口径）。
2. **HMDFS make jobserver mkfifo 失败**：`make -jN` 报
   `jobserver mkfifo: Operation not permitted`，make 可自动回退并行成功；
   为避免噪声日志本地手动构建建议 `make -j1`（SKILL 构建命令规范一致）。
   → 已有知识覆盖（SKILL.md 构建命令即 -j1），非新增。
3. **conan-verify G2 自动注入 ghfast 镜像**：工具在 E017 预防时临时注入镜像并恢复，
   配方内 URL 保持官方源。

## 知识路径决定
- 候选 1（上游版本字符串滞后）经查重评估：知识库中无同因条目（无匹配 error_signature），
  新增差异 = 「OpenDDL 解析器 tag 版本与源码 Version 不一致的判定口径」，可跨库复用
  （任何从源码读版本号的上游包都可能遇到）。
  → 路径 B（知识库扩展），建立 `DRAFT` 草稿对（.md/.kv）。

## 状态
- status: built（conan-verify 通过，未 upload；PR 合入后由 CI release 流水线发布）
---

**编译结束**: 2026-09-29 04:05
**最终状态**: built
