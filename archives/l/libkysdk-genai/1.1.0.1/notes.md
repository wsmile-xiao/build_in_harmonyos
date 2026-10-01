# libkysdk-genai 1.1.0.1 适配笔记

## 上游
- 仓库: https://gitee.com/openkylin/libkysdk-genai-nlp.git（openKylin；本项目名 libkysdk-genai）
- tag: upstream/1.1.0.1, commit 47f0725acc1c038e9062989b3b260a09f7d2cc42（R39 合规官方源）
- Build-Depends（Ubuntu）: cmake、libssl-dev、libjsoncpp-dev、libjson-glib-dev、
  libglib2.0-dev、libkylin-ai-system-private-dev（KylinAiProto）、libkysdk-ai-common-dev

## 结构（CMake，C++17）
- 顶层 `add_library(kysdk-genai-nlp SHARED)`：src/ 下
  `_chatmessage/_chatmodelconfig/_chatresult/_genaitextsession/genainlpserver/
  genainlpserviceproxy/logger` + gdbus 生成 glue（gennlpserviceglue.c/h）
- 产物: `libkysdk-genai-nlp.so` + `include/kylin-ai/genai/text/`（chat/chatmessage/
  config/error/result 头）+ `usr/share/pkgconfig/kysdk-genai-nlp.pc`
- 关键依赖: find_package(OpenSSL REQUIRED) / find_package(KylinAiProto REQUIRED)
  / find_package(KysdkAiCommon REQUIRED) / pkg_check_modules(GIO gio-unix-2.0)
  / find_package(jsoncpp) / kylin_ai_generate_gdbus_proto_code(gennlpservice)
  / pkg_check_modules(JSON json-glib-1.0)

## 适配要点（4 个补丁）
1. 0001: jsoncpp include 前缀 `#include <jsoncpp/json/value.h>` /
   `"jsoncpp/json/json.h"` → `<json/value.h>` / `"json/json.h"`
   （制品仓 jsoncpp 头在 include/json/，同 libkysdk-ai-private 0002）
2. 0002: 主 CMakeLists——`find_package(jsoncpp REQUIRED)` → `find_package(JsonCpp
   CONFIG REQUIRED)` + target `jsoncpp` → `JsonCpp::JsonCpp`（制品仓 jsoncpp 只导出
   JsonCpp::JsonCpp）；`pkg_check_modules(GIO/JSON)` 后补
   `link_directories(${GIO_LIBRARY_DIRS} ${JSON_LIBRARY_DIRS})`（-L 不传给 lld 则
   -lgio-2.0/-ljson-glib-1.0/-lffi/-lpcre2-8 找不到，同 libkysdk-ai-private 0001）；
   补 `include_directories(${AI_COMMON_INCLUDE_DIRS}/kylin-ai)`（`#include <common/...>`
   上游依赖系统 /usr/include/kylin-ai 前缀）；`install(DIRECTORY usr/ DESTINATION /usr)`
   越权写系统根 → `DESTINATION .`（相对前缀，配合 conan package() --prefix 落到包内
   share/pkgconfig）；注入 `-Wl,-soname,libkysdk-genai-nlp.so`（CMake 无 HarmonyOS
   平台模块，VERSION/SOVERSION 不生成 SONAME，同 kysdk-ai-common 0001）
3. 0003: KylinAiProtoFunctions.cmake 硬编码 `/usr/share/kylin-ai/protocols/gdbus/`
   与 `/usr/bin/gdbus-codegen` → `${KYLAI_GDBUS_PROTOCOL_DIR}` /
   `${KYLAI_GDBUS_CODEGEN}`（base_path vendor/kylin-ai-proto，同 libkysdk-ai-private 0003）
4. 0004: ai-proto 顶层 CMakeLists `install(DIRECTORY protocols/usr/ DESTINATION /usr)`
   越权 → `${CMAKE_INSTALL_PREFIX}`（base_path vendor/kylin-ai-proto，同 0004）

## 关键坑（本库特有/复用）
1. **KylinAiProto 制品仓缺失**：libkysdk-ai-private 构建期 vendor 的 kylin-ai-proto
   未在其 package() 导出。libkysdk-genai 的 find_package(KylinAiProto REQUIRED) +
   kylin_ai_generate_gdbus_proto_code 宏无法从制品仓获得 → 复用 libkysdk-ai-private
   的 vendor 方式：get openkylin/libkylin-ai-system-private debian/1.2.0.1-1 内嵌
   ai-proto（含 gennlpservice.xml），构建到 build_folder/staging，generate() 注入
   KylinAiProto_DIR（staging/share/KylinAiProto/cmake）+ KYLAI_GDBUS_CODEGEN/
   KYLAI_GDBUS_PROTOCOL_DIR。注意用 KylinAiProto_DIR 而非覆盖 CMAKE_PREFIX_PATH
   （会屏蔽 CMakeDeps 生成的 JsonCpp/OpenSSL Config）。
2. **json-glib ↔ glib 版本冲突**：json-glib/1.10.6 配方 pin glib/2.84.0.1，而
   libkysdk-ai-private 已发布二进制依赖 glib/2.88.0.1（gio-unix + gdbus-codegen）。
   conan 图直接报 Version conflict。解决：requirements() 内
   `self.requires("glib/2.88.0.1", override=True, ...)` 统一到 2.88.0.1，json-glib
   在本图按 `--build=missing` 重编一次（meson，数分钟，本地缓存复用；CI 同理）。
   如不 override 而统一到 2.84 则会重建 libkysdk-ai-private（含 gtest/mock，更慢）。
3. **ambient LDFLAGS 污染**：CMake configure 期读取进程环境 LDFLAGS 注入
   CMAKE_*_LINKER_FLAGS。本机/CI shell 若 export LDFLAGS=-L$DEFAULT_PREFIX/lib，
   会把 /usr/local/lib 下的共享 glib（libgio-2.0.so.0 等）误链进产物（实测 NEEDED
   出现共享 glib，R26 风险）。修复：generate()/build() 显式 `os.environ["LDFLAGS"]=""`，
   保证只链 Conan 依赖（glib 为静态包，链入后 NEEDED 仅 libjson-glib-1.0.so.0 /
   libjsoncpp.so / libc++_shared.so / libc.so）。
4. **usr install 绝对/相对前缀**：`install(DIRECTORY usr/ DESTINATION /usr)` 在 conan
   package() 写系统根报 Operation not permitted。改 `${CMAKE_INSTALL_PREFIX}` 仍是
   configure 期绝对路径（--prefix 不影响），必须改相对 `DESTINATION .`（contents of
   usr/ → 前缀根）才能配合 conan `cmake --install --prefix <package_folder>` 落包内
   share/pkgconfig。
5. **SONAME**：CMake 无 HarmonyOS 平台模块，`set_target_properties(VERSION SOVERSION)`
   不产生 -Wl,-soname，L5 门禁会查 DT_SONAME → 补 target_link_options。
6. **glib 静态包 + ffi/intl 内嵌**：glib 为静态包，libffi.a/libintl.a 内嵌其 lib/，
   pkg_check_modules(GIO) 返回 -lffi/-lintl 但无对应 -L；`link_directories(${GIO_LIBRARY_DIRS})`
   （含 <glib>/lib）即解析。pcre2/z 的 -L 也随 GIO_LIBRARY_DIRS 提供。
7. **OHOS 动态链接器要求签名 ELF**：SDK lld 产物自带 .codesign 段，签名前 objcopy
   移除，再 binary-sign-tool -selfSign 1（package() 与 test_package 均需；未签名
   二进制实测 rc=126 Permission denied）。
8. **gitee 归档反爬**：/repository/archive/ 端点对 conan Python urllib 返回 HTML
   反爬页，sha256 每次不同；主源码用 git clone 官方源 + 固定 commit（R39）；
   kylin-ai-system 归档用 curl UA 的 get()（同 libkysdk-ai-private）。

## 上游测试申报表（R51 三步法）
| 项 | 值 |
|---|---|
| 上游用例数（函数级） | 10（test01-test09 + test10_BigTest） |
| 上游用例数（执行点口径） | 29（test10_BigTest 内部重复 test10_Chat 20 次 + 其余 9） |
| 上游测试真实执行数 | 10/10（执行点 29/29，OHOS 本地实测，见 reports/upstream/testGenAiNlp-run.log） |
| 上游测试通过数 | 0 |
| 上游测试通过率 | 0/10（0%）；非未执行——每个用例均已真实运行，全部在 `genai_text_init_session` 因无 AI 运行时服务返回 AISDK_RUNTIME_ERROR（错误码 3），具体报错定位见下方逐项证据 |
| 适配后运行数 | 16（鸿蒙特有实质测试断言数，test_package/test.cpp） |
| 通过数 | 16 |
| 通过率 | 适配后 16/16 断言通过 |

清点证据（tag upstream/1.1.0.1, commit 47f0725a）:
1. tests/ 目录含 CMakeLists.txt + testGenAiNlp.cpp（451 行）
2. 测试函数清单（10 个）：
   - test01_Chat / test02_ChatHistoryMessages / test03_ClearChatMessage /
     test04_SetModelConfig / test05_SetChatSystemPrompt / test06_GenerateContent /
     test07_ChatSystemPromptId_SUMMARY / test08_ChatSystemPromptId_TEXT_EXPANSION /
     test09_ChatSystemPromptId_TRANSLATE_CHINESE_TO_ENGLISH / test10_BigTest
   - test10_BigTest 内部 `test10_Chat()` 重复调用 20 次（一~二十）
3. 真实执行结果（OHOS 本地实测，10 用例/29 执行点全部执行，程序正常退出 rc=0）：
   - 已真实编译并运行上游测试程序 testGenAiNlp（链接本包 libkysdk-genai-nlp.so +
     依赖链，stdin 重定向 /dev/null，完整日志见 reports/upstream/testGenAiNlp-run.log）
   - 每个用例先调 `genai_text_init_session`：无 AI 运行时服务（D-Bus socket
     /tmp/.kylin-ai-runtime-unix/<uid>/genai-nlp.sock 不存在）→ 重连退避 10 次后
     返回错误码 3（AISDK_RUNTIME_ERROR），`LOGE("初始化错误：错误码 3")` 后 return；
     29 个执行点全部打印 `初始化错误：错误码 3`（日志中 29 次命中，与执行点口径一致）
   - 关键点：init 失败 return 发生在创建 ctrlThread / g_main_loop_run / getchar 之前，
     故无 AI 服务时程序**不会**卡在交互式等待——10 个用例依次真实执行完毕并退出
   - 后续 `chat_async`/`generate_content_async` 依赖真实 AI 云服务认证（百度 ERNIE /
     讯飞 Spark，认证串为空），因 init 未成功而未触达——这是环境约束（OHOS 无 AI
     云服务账号/网络），每个用例的失败均落在 init 错误路径，有具体错误码定位
4. 适配后可运行的实质测试（test_package/test.cpp，R34 非空壳，16 断言，实测 16/16）：
   - 对象生命周期：ChatModelConfig / ChatMessage / GenAiTextSession 建/毁
   - genai_text_init_session 无 AI 运行时服务（/tmp/.kylin-ai-runtime-unix/<uid>/
     genai-nlp.sock 不存在）→ 连接失败重连退避后返回 AISDK_RUNTIME_ERROR（真实
     错误路径，实测 ~10s）
   - chat_result_get_* 空指针默认值（NLP_INPUT_INVALID / nullptr / true）
   - PromptId / ModelDeployType / AiSdkCommonErrorCode 枚举值

## 依赖版本
- kysdk-ai-common/1.1.0.1（find_package(KysdkAiCommon) + pkg kysdk-ai-common）
- libkysdk-ai-private/1.1.0.1（kyai 族，W0 确认系列依赖）
- glib/2.88.0.1（静态包，gio-unix-2.0.pc + gdbus-codegen；override 统一版本）
- jsoncpp/1.9.8（JsonCpp::JsonCpp）
- json-glib/1.10.6（本图重编于 glib 2.88）
- openssl/3.5.8.1（仅 find_package 满足，源码未直接使用）

## 验证结果
```bash
# 手动编译（模式 B）：cmake configure/build/install → libkysdk-genai-nlp.so
#   NEEDED: libjson-glib-1.0.so.0, libjsoncpp.so, libc++_shared.so, libc.so
#   SONAME: libkysdk-genai-nlp.so
# conan-verify G0-G4/L2/L4/L5: 见 reports/conan-verify-report.md
# W3 本地 CI: conan create（含 test_package ctest 16/16）
# conan create 内嵌 ctest: 16/16 passed（.ci_logs/conan_build_*.log）
# 上游测试真实执行（OHOS 本地实测）：
#   编译 testGenAiNlp（链接本包 .so + 依赖链）→ 签名 → 运行（stdin </dev/null）
#   10 用例/29 执行点全部真实执行，程序退出 rc=0
#   每个用例在 genai_text_init_session 无 AI 运行时服务返回 AISDK_RUNTIME_ERROR
#   （错误码 3），日志命中 29 次 "初始化错误：错误码 3"
#   完整日志: reports/upstream/testGenAiNlp-run.log
```

## 交付物
| 文件 | 说明 |
|------|------|
| lib/libkysdk-genai-nlp.so | 主共享库（签名 ELF，SONAME libkysdk-genai-nlp.so） |
| include/kylin-ai/genai/text/*.h | chat/chatmessage/config/error/result 头文件 |
| share/pkgconfig/kysdk-genai-nlp.pc | pkg-config 描述（Cflags 含 -I/usr/include/kylin-ai 为上游遗留，Conan cpp_info 接管） |

## 平台注意
- package_info: cmake_file_name=KysdkGenAiNlp, cmake_target_name=
  KysdkGenAiNlp::KysdkGenAiNlp, pkg_config_name=kysdk-genai-nlp,
  libs=['kysdk-genai-nlp'], includedirs=['include']
- 运行时依赖 libjson-glib-1.0.so.0 / libjsoncpp.so / libc++_shared.so / libc.so
  （Conan 依赖链自动提供；glib 静态链入）
- 上游 10 个交互式测试无法在 OHOS CI 运行（见申报表）；test_package 为鸿蒙
  特有实质测试（16 断言）
---

**编译结束**: 2026-09-29 09:18
**最终状态**: built
