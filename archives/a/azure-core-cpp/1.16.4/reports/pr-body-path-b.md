# 积分赛 PR 正文（路径 B）

- **三方库名称**：azure-core-cpp
- **上游版本**：1.16.4
- **上游仓库地址**：https://github.com/Azure/azure-sdk-for-cpp
- **适配路径**：路径 B（贡献创新）
- **使用知识库**：E321-conan-get-url-no-extension-badzipfile（codeload get() filename 参数复用）；DRAFT-azure-core-cpp-1.16.4-cmake-platform-detection（CMake 平台三分支检测对 HarmonyOS 落入 else() FATAL 的新增草稿）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 140 | 来源：sdk/core/azure-core/test/ut/（gtest 1.17.0，25 套件） |
| 集成测试 | 0（排除） | 网络/凭据/云服务测试因 Azure 端点不可达离线排除 |
| 其他测试 | 0 | 无 |
| **合计** | **140** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 140 | 不变 | 全部 140 测试通过（0 失败 0 跳过） |
| 集成测试 | 0 | 排除 | 网络/凭据/云服务测试因离线环境排除 |
| 鸿蒙特有测试 | 1（test_package） | 新增 | 消费者验证：UUID/DateTime/URL/Context API 正确性 |
| **合计** | **141** | **+1** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：140/140（100%）
- 新增测试用例通过率：1/1（100%）

## 补充说明

### 路径 B 知识扩展
- 新增 `knowledge/drafts/azure-core-cpp-1.16.4-cmake-platform-detection.{kv,md}`：上游 CMake 平台三分支（if(WIN32)/elseif(UNIX)/else() FATAL_ERROR）不识别 HarmonyOS 的检测模式与最小修复（patch: `elseif (UNIX OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")`）。
- 复用 `knowledge/drafts/E321-conan-get-url-no-extension-badzipfile.kv`：codeload 无扩展名 URL 下载的 get() BadZipFile 问题，按 E321 建议在 source() 中显式传递 `filename` 参数。

### 已知限制
- 排除测试：Azure 网络/凭据/云服务测试（http_test、bearer_token、curl_session、transport_adapter 等），因离线环境无法访问 Azure 端点。本地替代：test_package 消费者验证 + 140 纯单元测试。
- OHOS `/tmp` 只读限制：gtest 流捕获需补丁启用 TMPDIR 环境变量（已有仓库 gtest 1.17.0 的 0001-tmpdir-ohos-sandbox.patch）。
- CMake `CMAKE_SYSTEM_NAME=HarmonyOS` 平台模块缺失：仅影响 FindOpenSSL 模块模式（已通过 CMakeDeps 传递路径解决，详见 recipe）。

### 变更文件清单
1. `archives/a/azure-core-cpp/1.16.4/conandata.yml` — 源码 URL + SHA-256 + patches 声明
2. `archives/a/azure-core-cpp/1.16.4/conanfile.py` — Conan recipe（openssl + libcurl 依赖，azure-core 子项目构建）
3. `archives/a/azure-core-cpp/1.16.4/manifest.yaml` — 版本 manifest
4. `archives/a/azure-core-cpp/1.16.4/notes.md` — 构建说明 + OHOS 限制记录
5. `archives/a/azure-core-cpp/1.16.4/patches/0001-add-harmonyos-platform-support.patch` — HarmonyOS 平台识别补丁
6. `archives/a/azure-core-cpp/1.16.4/test_package/conanfile.py` — Conan L1 测试
7. `archives/a/azure-core-cpp/1.16.4/test_package/CMakeLists.txt` — 消费者 CMake 配置
8. `archives/a/azure-core-cpp/1.16.4/test_package/test.cpp` — 消费者验证代码
9. `knowledge/drafts/azure-core-cpp-1.16.4-cmake-platform-detection.kv` — 路径 B 知识草稿（kv）
10. `knowledge/drafts/azure-core-cpp-1.16.4-cmake-platform-detection.md` — 路径 B 知识草稿（md）