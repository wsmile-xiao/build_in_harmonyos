# libkysdk-ai-private 1.1.0.1 — 适配笔记

## 上游
- 仓库: https://gitee.com/openkylin/libkysdk-ai-private（openKylin 孵化期）
- 默认分支仅 README 空壳（无 1.1.0.1 归档/tag）；官方发布渠道为打包源
- 源码: Ubuntu pool `libkysdk-ai-private_1.1.0.1.orig.tar.gz`（openKylin 官方打包源）
  - url: http://archive.ubuntu.com/ubuntu/pool/universe/libk/libkysdk-ai-private/libkysdk-ai-private_1.1.0.1.orig.tar.gz
  - sha256: 16b8ad96f279fc456c2f85bde392b5e819886920ffda3103c070cb6d84881a9e
- Build-Depends（Ubuntu）: cmake、libglib2.0-dev、libjson-glib-dev、libjsoncpp-dev、
  libkylin-ai-system-private-dev、nlohmann-json3-dev、pkgconf

## 结构（CMake，顶层 add_subdirectory 三个子库）
- `ai-config/` → libkyai-config.so（AI 配置服务客户端；jsoncpp + GIO gio-unix-2.0 +
  KylinAiProto gdbus glue；ENABLE_TEST=OFF 时 tests/ 子目录不构建——发行源码中不存在）
- `ai-assistant/` → libkyai-assistant.so（AI 助手服务客户端；jsoncpp + GIO + KylinAiProto
  gdbus glue；-fvisibility=hidden）
- `libkyai-data-management-client/` → libkyai-data-management-client.so（AI 数据管理客户端；
  GIO + nlohmann_json + KylinAiProto gdbus glue；含上游 GTest 测试 test/units-test）

## 适配要点（4 个补丁）
1. 0001: 三个子 CMakeLists——`find_package(jsoncpp REQUIRED)` → `find_package(JsonCpp
   CONFIG REQUIRED)` + target 改 `JsonCpp::JsonCpp`（制品仓 jsoncpp CMakeDeps 目标）；
   `pkg_check_modules(GIO)` 后补 `link_directories(${GIO_LIBRARY_DIRS})`（-L 不传给 lld
   则 -lgio-2.0 找不到，同 ayatana/speech 模式）；`install(DIRECTORY usr/ DESTINATION /usr)`
   与 `install(FILES ... DESTINATION /usr/share/pkgconfig)` 绝对路径越权 → `${CMAKE_INSTALL_PREFIX}`
2. 0002: jsoncpp include 前缀——`#include <jsoncpp/json/json.h|value.h>` → `<json/json.h|value.h>`
   （制品仓 jsoncpp 头文件在 include/json/，同 speech 0005）
3. 0003: KylinAiProtoFunctions.cmake 硬编码 `/usr/bin/gdbus-codegen` 与
   `/usr/share/kylin-ai/protocols/gdbus/` → `${KYLAI_GDBUS_CODEGEN}` / `${KYLAI_GDBUS_PROTOCOL_DIR}`
   （同 speech 0002）
4. 0004: ai-proto `install(DIRECTORY protocols/usr/ DESTINATION /usr)` 绝对路径越权
   → `${CMAKE_INSTALL_PREFIX}`（同 speech 0004）

## 关键坑：协议 XML 版本错配（本库特有）
- 现象：gdbus-codegen 生成 glue 后编译报 `use of undeclared identifier
  'ai_runtime_config_service_call_get_free_trial_models_sync'` 与 `no matching function
  for call to 'ai_runtime_assistant_call_prompts_sync'`（源码传 sessionId 5 参，glue 只有
  proxy+out+cancellable+error 4 参）。
- 根因：libkysdk-ai-private 1.1.0.1 源码期望的协议（configservice/assistantservice XML）比
  **独立 kylin-ai-proto 仓库**（upstream 分支及所有发行分支）旧一版——独立仓库 XML 缺
  getFreeTrialModels / get_configured_nlp_model_list / set_current_nlp_model 与
  prompts 的 session_id 参数。协议随 **libkylin-ai-system-private 1.2.0.1 内嵌 ai-proto**
  演进，独立仓库未同步。
- 修复：vendor 协议源改用 openkylin/libkylin-ai-system-private `debian/1.2.0.1-1` 内嵌
  ai-proto（gitee archive，curl UA），source() 里把 ai-proto 挪到 vendor/kylin-ai-proto。
- 诊断特征：编译期 `use of undeclared identifier 'ai_runtime_*'` + `no matching function
  for call`；对照 glue.h 的 *_sync 签名参数数 < 源码调用参数数，即为协议版本错配。

## 其他
- gitee 归档按 User-Agent 过滤，get() 显式传 `headers={"User-Agent": "curl/8.0"}`
- 制品仓依赖: glib/2.88.0.1（gio-unix-2.0.pc + gdbus-codegen）、jsoncpp/1.9.8、
  nlohmann-json/3.11.2；私有依赖 kylin-ai-proto 制品仓无配方 → 配方内 vendor（L0i）
- OHOS 动态链接器要求签名 ELF：objcopy 去 .codesign + binary-sign-tool -selfSign 1，
  签名后 chown-to-self + chmod 0755（HMDFS 跨 app 读/执行位兜底，同 speech）
- 上游测试: libkyai-data-management-client/test/ GTest units-test 13 个 TEST_F，依赖
  kylin-ai-runtime AI 数据管理服务端 session，CI 无服务进程不可真实执行——申报 N=13
  （13 个 TEST_F 清单见 MANIFEST，实测 13 ≤ 声明 13，不少报）；可运行 0（有具体技术
  原因：环境缺 AI 服务端 session）；新增消费者冒烟 1 入口（探针 3 .so dlopen/读校验
  + 3 头文件检查）
- 路径判定: A + B（gdbus 协议 XML 版本错配诊断 + 读校验探针是可跨库复用的模式：
  kylin-ai 系列消费者遇 glue 签名不匹配，先查协议版本是否匹配源码）
