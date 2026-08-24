**【申请人账号】** junshi_liu

**【队伍名称】** 兰州大学DSLab

**【申请日期】** 2026/08/22

**【库名称】** azure-core-cpp

**【版本】** 1.16.4

**【关联 PR】** #6204（https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/6204）

**【分支信息】** feat/azure-core-cpp-1.16.4 → main

**【当前提交】** f38443f09eef8ec11c95d7f8404ff374f3e321f7（包含 Issue 正文元数据更新）

**【PR 状态】** 开放中

**【当前 CI】** 截至回读时尚未确认（未获取到远端 CI 通过证据，不得宣称已通过）

## 一、申请路径 B 的理由

Azure Core C++ 1.16.4 是 Microsoft Azure SDK for C++ 的核心基础库，提供 HTTP 客户端、UUID、DateTime、URL 解析、JSON、Context 与 Cancellation 等跨平台基础设施。在 OHOS armv8（clang15、libc++、C++17、Release）本地适配中，recipe 构建、消费者验证及上游测试均完成。适配过程中识别出一个真实、可跨库复用的 OHOS 平台诊断模式（上游 CMake 平台三分支检测不识别 HarmonyOS），且已形成最小修复与完整验证证据，满足路径 B 贡献创新条件。

## 二、推广价值

上游 CMake 惯用的 `if(WIN32) elseif(UNIX) else() message(FATAL_ERROR "Unsupported platform.")` 平台三分支判定结构在多个 C/C++ 项目存在；OHOS 工具链将 `CMAKE_SYSTEM_NAME` 设为 `HarmonyOS`，既非 WIN32 也非 UNIX，会落入 else() 直接 FATAL。本知识条目将该模式与最小修复（`elseif (UNIX OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")`）沉淀为跨库诊断模板，可复用于所有使用同类三分支的平台适配，提升 OHOS 移植效率。

## 三、知识库查重与新增价值

已按 main 最新状态对 knowledge/graph、knowledge/drafts、knowledge/doc 执行关键词与语义等价查重：

- **新增草稿**：`knowledge/drafts/azure-core-cpp-1.16.4-cmake-platform-detection.kv`（配对 `.md`：`knowledge/drafts/azure-core-cpp-1.16.4-cmake-platform-detection.md`），记录 CMake 平台三分支检测对 HarmonyOS 落入 else() FATAL 的根因、最小 patch、验证方式与查重结论。拟提升编号由主编确认。
- **复用知识**：`E321-conan-get-url-no-extension-badzipfile`（codeload 无扩展名 URL 的 conan get() BadZipFile）。E321 仅作为复用知识，不重复申报为新增草稿。
- **查重不适用项**：E265-draft-2301 为 autotools 正向能力探测（不同构建工具链），E322-draft-F2BA 为 HarmonyOS 缺失 Platform/HarmonyOS.cmake 导致的 SONAME 问题（不同阶段），均不适用。

## 四、证据表

| 类别 | 证据 | 说明 |
|------|------|------|
| 原始失败 | 本地 `AzureTransportAdapters.cmake:73 Unsupported platform` | 本地首轮失败，无 CI 编号（远端 CI 尚未运行） |
| 修复方案 | `patches/0001-add-harmonyos-platform-support.patch` | HarmonyOS CMake 平台分支识别：`elseif (UNIX OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")` |
| 构建验证 | OHOS armv8 / clang15 / libc++ / C++17 / Release；`conan create` 成功 | 产物 libazure-core.so + 52 头文件 + CMake config |
| 上游测试 | 140/140 PASS，25 个测试套件 | gtest 1.17.0；网络/凭据/云服务测试排除，本地替代证据齐全 |
| 消费者验证 | `test_package` 1/1 PASS | 真实 CMake config、链接和运行通过（UUID/DateTime/URL/Context） |
| 审查证据 | 无人工 review 记录 | 不手工 `/ai review`，如实标注 |
| 当前 CI 证据 | 尚未确认 | 截至回读时未获取远端 CI 通过证据 |

## 五、测试框架迁移类说明

不适用（本库为 CMake + gtest 原生测试，无测试框架迁移需求）。

## 六、路径 B 贡献创新：10 分候选

本条目为新增跨库诊断模式，非简单复用：上游 CMake 平台三分支检测对 HarmonyOS 的识别缺口与最小补丁方案，形成可迁移的 OHOS 适配模板，符合路径 B 贡献创新 10 分候选标准。

## 七、其他说明

- 上游测试排除说明：Azure 网络/凭据/云服务测试（http_test、bearer_token_authentication_policy、curl_session、transport_adapter 等）因离线环境无法访问 Azure 端点而被排除，本地替代证据为 test_package 消费者验证（1/1）与 140 个纯单元测试全部通过；网络/凭据测试未伪造通过。
- OHOS 运行时限制：`/tmp` 只读，gtest 流捕获使用 TMPDIR 环境变量（应用仓库已有 gtest 1.17.0 的 0001-tmpdir-ohos-sandbox.patch）。
- 路径 A、依赖附加分和路径 C 均不单独申报：本任务核心贡献为路径 B 知识扩展；依赖图（openssl/3.5.6、libcurl/8.5.0、zlib/1.3.1.1）为普通适配事实，无独立附加分申报；无路径 C 证据（无私有工具链/汇编/超大依赖）。

## 八、三个官方确认问题

1. 请确认拟提升的知识草稿编号（当前草稿 `azure-core-cpp-1.16.4-cmake-platform-detection` 待主编指派正式 E 编号）。
2. 请确认远端 CI 运行状态与审查结论（当前 CI 状态截至回读时尚未确认，待 PR #6204 关联 CI 完成后核验）。
3. 请确认合并准入条件（W0-W5、Review、CI、合并）是否满足；合并前任何宣称"已通过"均不成立。