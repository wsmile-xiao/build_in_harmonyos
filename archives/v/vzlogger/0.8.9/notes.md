# vzlogger 0.8.9 — 适配笔记

## 概述
- 软件：vzlogger（volkszaehler.org 智能电表数据采集/上报守护进程）
- 构建系统：CMake（init-build 猜测 autotools 有误，以源码 CMakeLists.txt 为准）
- 上游 tag：v0.8.9（449fe69bcb7fa07959adf3bd076d419f812ad656）

## 编译适配
本地编译成功，`vzlogger --version` 输出 0.8.9。构建选项：
`-DENABLE_SML=OFF -DENABLE_OMS=OFF`（见"可选特性"）

### 源码修改（12 处，详见 patches）
1. `include/shared_ptr.hpp`：`<tr1/memory>` → `<memory>`，`std::tr1::shared_ptr`/`enable_shared_from_this` → `std::`（OHOS libc++ 无 TR1 头）
2. `include/threads.h`：CANCELLABLE/_safe_to_cancel/_cancellable_sleep 增加 `HAVE_PTHREAD_CANCEL` 守卫分支（E127：OHOS 无 pthread_cancel）
3. `include/Channel.hpp`：新增 `_stop_requested` 标志、`stopRequested()`；cancel() 协作式（broadcast 唤醒）；wait() 检查标志
4. `src/Channel.cpp`：构造函数初始化 `_stop_requested`
5. `include/MeterMap.hpp`：新增 `_stop_requested`、`stopRequested()`
6. `src/MeterMap.cpp`：cancel() 协作式（pthread_cancel 分支守卫 + stop_requested 置位 + join）
7. `src/threads.cpp`：reading_thread/logging_thread 主循环改 stopRequested 检查；MQTT 发布 `if (&*it)` 恒真修复（clang15 -Werror）；pthread_setcancelstate 守卫
8. `src/CurlSessionProvider.cpp`：pthread_testcancel → _safe_to_cancel（经 threads.h 兼容层）
9. `include/Options.hpp` + `src/Options.cpp`：lookup_string_tolower 返回类型 const char* → std::string（clang15 -Wreturn-stack-address）
10. `src/protocols/MeterRandom.cpp`：`(float)rand()/(float)RAND_MAX`（clang15 隐式转换警告）
11. `CMakeLists.txt`：CheckSymbolExists 检测 pthread_cancel → HAVE_PTHREAD_CANCEL；curl/gnutls include 目录传播；tests/mocks 目标 -std=c++17（gtest 1.17 要求）
12. `modules/FindGnutls.cmake`：移除 sasl2 硬编码静态依赖猜测（OHOS 无 libsasl2）

### 测试构建环境修正
- `tests/CMakeLists.txt`：gtest/gmock 头文件路径传播（FindGTest config-mode 的 include 目录）+ -std=c++17
- `tests/mocks/CMakeLists.txt`：同上 + microhttpd include

## 可选特性决策（方案 A：关闭）
| 特性 | CMake 选项 | 原因 | 功能损失面 |
|---|---|---|---|
| SML 电表协议 | ENABLE_SML=OFF | 制品仓 `sml/1.1.11` 实为 Boost.SML（boost/sml.hpp 状态机库），**非** vzlogger 所需 volkszaehler libsml（sml/sml_file.h 智能电表协议库），同名不同库 | MeterSML.cpp 不编译；SML（EDL-21/eHz/SyM² 表）协议不可用 |
| OMS/M-Bus 协议 | ENABLE_OMS=OFF | libmbus 未在制品仓发布 | MeterOMS.cpp 不编译；OMS（M-Bus）表协议不可用 |
- 保留：ENABLE_LOCAL（本地 HTTPd，libmicrohttpd 已发布）、ENABLE_MQTT（mosquitto 已发布）、BUILD_TEST（gtest 已发布）
- 主协议 file/exec/random/s0/d0/fluksov2/w1therm 全部可用；主功能（采集+上报 volkszaehler/influxdb/mysmartgrid/null API）完整

## 测试结果
- ctest 4 项：mock_metermap / mock_MeterW1therm / mock_MeterS0 通过；vzlogger_unit_tests 43 子测试 32 通过 + 11 平台限制失败
- 11 项失败全部因 `mkfifo`（OHOS 平台限制，穷尽验证）：
  - `/tmp`：erofs 只读（E002）
  - `$HOME/tmp`、构建目录：HMFS EPERM（不支持 FIFO 特殊节点）
  - `/dev/shm`、tmpfs 根：EACCES
  - `tmpnam()` 固定 /tmp，TMPDIR 无效；pty 不完整
  - 影响：MeterD0×7 + MeterFile×4（FIFO 模拟电表设备输入）
- `api_Volkszaehler.config_options` 原失败（示例配置含 sml 协议段，SML 关闭后解析抛 "Protocol not found"）→ 按上游 OCR 处理范式从示例配置移除不可用协议段后通过

## 知识候选（详见 task-gate）
1. OHOS libc++ 无 tr1/memory → std 迁移（跨软件通用）
2. OHOS musl 无 pthread_cancel → 协作式 stop_flag + pthread_join（E127 已有，本任务补充实现范式）
3. OHOS HMFS 不支持 mkfifo → FIFO 依赖测试需普通文件替代（新知识候选）
4. gtest ≥1.17 需 C++17 而全局 -std=c++11 → 目标级覆盖（可能新知识）
5. FindGnutls/cmake 依赖探测硬编码兜底在 OHOS 会命中缺失库（sasl2）（可能新知识）

## 依赖版本（conan 制品仓）
json-c/0.18、libcurl/8.5.0、gnutls/3.8.10（传递 nettle/libtasn1/gmp/libgpg-error）、openssl/3.5.6.1（mosquitto 约束）、libuuid/2.40.4、libgcrypt/1.11.0（gnutls 约束）、libunistring/1.0、libmicrohttpd/1.0.1、mosquitto/2.0.18、gtest/1.17.0.2
---

**编译结束**: 2026-09-23 12:53
**最终状态**: published
