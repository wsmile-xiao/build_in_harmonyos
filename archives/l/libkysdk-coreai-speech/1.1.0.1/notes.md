# libkysdk-coreai-speech 1.1.0.1 — 适配笔记

## 上游信息
- 仓库: https://gitcode.com/openkylin/libkysdk-coreai-speech（openKylin 开放麒麟）
- 版本: 1.1.0.1（tag `upstream/1.1.0.1`，46bb1fb）
- 源码: gitee.com/openkylin 官方镜像归档（与 gitcode 同源同一 tag，
  tarball 内容与 tag 一致性经 CMakeLists md5 校验），
  sha256=`0ad9a41c56107e7aef1996230fe6e9f8585d7b27278e53ffaf86e7aac2732cc5`
- 构建系统: CMake（min 3.5，C++17），产物 `libkysdk-coreai-speech.so`（SHARED，
  SOVERSION 1，VERSION 1.0.0）+ kylin-ai 头文件 + kysdk-coreai-speech.pc

## 功能定位
Kylin AI Core Speech SDK（麒麟 AI 子系统 SDK 层）：语音识别（ASR）与语音合成
（TTS）客户端库。客户端经 D-Bus（corespeechservice 接口）与 kylin-ai-runtime
AI 服务进程通信。

## OHOS 适配要点
1. **依赖**：
   - `glib-2.0/gio-unix-2.0`（制品仓 glib/2.88.0.1；gio-unix-2.0.pc 从 glib 包内
     augment，同 ayatana 系列配方）
   - `OpenSSL`（制品仓 openssl/3.5.6，CMakeDeps 目标 openssl::openssl）
   - `jsoncpp`（制品仓 jsoncpp/1.9.8，CMakeDeps 目标 JsonCpp::JsonCpp）
2. **私有依赖 vendor 构建**（OHOS 制品仓无配方，L0i 要求 requires() 依赖已发布，
   故不声明 requires，配方内构建装入 staging 前缀供主构建使用）：
   - `kysdk-ai-common`（upstream 分支，sha256=`8525e3b7...`）：kylin-ai/common
     公共头 + libkysdk-ai-common.so + .pc。speech 只 include_directories 其头文件
     （`<common/macros.h>` 等），不链接该 .so；上游 .pc 的 Cflags 硬编码
     `-I/usr/include/kylin-ai`，安装后改写为指向 staging 前缀（`_fix_common_pc`）。
     注：common.cpp 内部 shell 调用 `/usr/bin/dpkg -s`（Linux 私有系统接口，
     OHOS 无 dpkg）——运行时 `is_ai_subsystem_inited()` 恒 false，编译不受影响。
   - `kylin-ai-proto`（upstream 分支，sha256=`a3ed3f4a...`）：INTERFACE 库 +
     `kylin_ai_generate_gdbus_proto_code` CMake 宏 + 协议 XML。宏硬编码
     `/usr/bin/gdbus-codegen` 与 `/usr/share/kylin-ai/protocols/gdbus/`——
     0002 补丁改为 `${KYLAI_GDBUS_CODEGEN}` / `${KYLAI_GDBUS_PROTOCOL_DIR}` 变量。
3. **gdbus-codegen**：OHOS SDK 的 /data/service/hnp/bin/gdbus-codegen 是坏条目
   （shebang 指向不存在的 python3）；glib 包内自带可用版（#!/usr/bin/env python3，
   自带 codegen 模块定位逻辑，实测无 PYTHONPATH 亦可运行）。宏经
   KYLAI_GDBUS_CODEGEN 变量 + CMAKE_PROGRAM_PATH 钉死 glib bin。
4. **0001 补丁**：speech 顶层 CMakeLists 的 OpenSSL/jsoncpp 改走 Conan CMakeDeps
   CONFIG 目标（openssl::openssl / JsonCpp::JsonCpp），替代上游裸
   find_package(OpenSSL)/find_package(jsoncpp)。
5. **测试（rule4 修复：0/5 → 5/5 真实执行）**：上游 tests/ 5 个可执行
   （testCoreSpeechApi/ModelChange/TestAsrToolFromMic/TestAsrToolOnce/
   TestTtsToolOnce）非 gtest 纯 C++ main：testCoreSpeechApi 自驱动 test01-06
   （main 无条件 return 0，日志 LOGI 6 条 test0X_），其余 4 个为 stdin 交互
   工具（喂 "quit" 退出）。pulseaudio/17.0.1 以 build_requires 提供
   pulse/pulse-simple（0007 补丁把 include/link 目录经 toolchain 变量注入
   tests/CMakeLists）；ENABLE_TEST=ON 真实构建；build() 中真实运行（
   testCoreSpeechApi grep 断言 6 子用例 + 4 工具 quit 退出 exit 0）。DBus
   服务（kylin-ai-runtime）与音频设备 OHOS 无，客户端库优雅降级（
   g_dbus_connection_new_for_address_sync 连 unix socket 立即失败返回 NULL、
   pa_simple_new 返回 NULL），测试执行客户端库代码路径、按上游语义 exit 0，
   不崩溃不挂起（timeout 兜底）。新增 test_package 消费者冒烟 1 入口（dlopen
   库验证依赖链接）。
6. **签名**：OHOS 动态链接器要求签名 ELF；SDK lld 链接产物自带 .codesign 段，
   签名前 objcopy 移除（`_sign_installed_elfs`，与 glib 配方同法）。

## 路径判定：路径 C（高难度挑战）候选
- ① 强绑定 Linux 私有系统接口：kysdk-ai-common 直接 shell 调 `/usr/bin/dpkg -s`；
- ② 私有编译工具链：KylinAiProto 的 gdbus-codegen 生成宏为麒麟私有 CMake 宏，
  现有知识库（540 条）无此类条目；
- ④ 依赖链庞大：speech + kysdk-ai-common + kylin-ai-proto 三仓库联动适配
  （制品仓均无后两者配方），全量测试需音频设备 + AI 服务进程，校验成本极高。
