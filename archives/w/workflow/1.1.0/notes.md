# workflow 1.1.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-12
- 编译器: clang/clang++ 15.0.4 (OHOS SDK 26.0.0.18, aarch64-linux-ohos, musl, libc++)
- 状态: published（conan create 全流程通过，上游测试 37/37+1 豁免，test_package HTTP 回环通过）

## 背景

平台任务 #7331。搜狗 workflow：C++ 并行计算与异步网络引擎
（HTTP/Redis/MySQL/DNS 协议 client+server、taskflow 图任务、算法任务、
文件任务）。适配 HarmonyOS PC (aarch64, musl, clang 15.0.4)。

## W0 依赖实测（conan download --only-recipe）

| 依赖 | 版本 | 实测结果 |
|---|---|---|
| openssl | 3.5.6 | ✅ ohpcd 有（仓内主流，72 处引用） |
| gtest | 1.17.0 | ✅ ohpcd 有（test_requires，跑上游测试用） |
| zlib/snappy/zstd/lz4 | - | KAFKA 组件所需，全部不需要（默认关闭） |

redis/mysql/consul/upstream 协议均为 workflow **内置实现**（无外部客户端库依赖），
保持上游默认开启——这是"可裁剪组件能关的关"核查后的结论：只有 KAFKA 引外部库，
且上游默认就是不启用。

## 平台差异与修复（核心知识）

### 1. musl msghdr.msg_iovlen 类型（补丁 0001）

glibc 的 `msghdr.msg_iovlen` 是 `size_t`，musl/OHOS 按内核 UAPI 原型是 `int`。
上游在 `__linux__` 分支强转 `(size_t)cnt`，在 C++11 初始化列表里构成 int→size_t
窄化，clang 报 `-Wc++11-narrowing` error。修法：判定改
`#if defined(__linux__) && defined(__GLIBC__)`，仅 glibc 走强转分支，musl 走
`cnt` 原型分支（语义不变，零平台宏新增）。

### 2. OHOS 内核 AIO 的 RESFD 通知无效（补丁 0002，⭐ 本适配最核心发现）

workflow 的文件任务（WFFileIOTask 等）用 Linux AIO：
- `IOService_linux.cc`：io_setup/io_submit + `IOCB_FLAG_RESFD`（每个 iocb 带
  eventfd，完成时内核写 eventfd → poller epoll_wait 唤醒）。

**OHOS 内核实测**（独立 syscall 复现程序验证）：
- `io_setup`/`io_submit`/`io_getevents` 本身正常（返回成功，数据写入正确）
- **但 `IOCB_FLAG_RESFD` 的 eventfd 完成通知路径无效**：io_submit 成功后
  epoll_wait(event_fd) 永不唤醒（超时返回 0）→ 上游 IOService_linux 的所有
  文件任务永久挂起（WFFileIOTask 卡死 1800s 超时）。

**修法**：workflow 自带 `IOService_thread.cc` 备胎（pthread 线程池模拟 AIO +
pipe 通知），接口与 linux 版一致，上游在非 Linux 平台（如 macOS/BSD）就走它。
补丁新增 `USE_THREAD_IOSERVICE` CMake 选项（默认 OFF 不改变上游行为）：
- 顶层 CMakeLists.txt 全局 `add_definitions(-DWORKFLOW_USE_THREAD_IOSERVICE)`
  （⭐ 必须全局：kernel/manager/factory 等所有翻译单元必须看到同一 IOService
  类布局，子目录级 add_definitions 会造成 vtable 错乱——见下）
- kernel/CMakeLists.txt 选用 IOService_thread.cc
- 两份 Communicator.h（kernel/ + include/workflow/）的
  `#ifdef __linux__` 选择判定加 `&& !defined(WORKFLOW_USE_THREAD_IOSERVICE)`
- Communicator.cc 的 io_bind/io_unbind/shutdown_io_service 分支同步
- CMakeLists_Headers.txt 的安装头清单同步（thread 模式装 IOService_thread.h）

**踩坑记录（R43 类调参螺旋，一次跳出）**：最初把 add_definitions 放在
kernel/CMakeLists.txt（子目录），结果 kernel/Communicator.cc 用 thread 版
IOService 布局（pipe_fd[2]），而 manager/WFGlobal.cc（new __FileIOService）
用 linux 版布局（io_ctx/event_fd）——**同对象两种类布局**，io_bind 写
pipe_fd[0] 写进 io_ctx 指针字段 → 读出垃圾负数 fd、std::mutex try_lock
假性失败（字段错位）。诊断手段：try_lock 探测 + 打印 this/mutex 地址 +
对比 sizeof(std::mutex)。修复：宏上提到顶层 CMakeLists 全局定义。

**消费者传导**：安装头 Communicator.h 的 IOService 选择判定依赖宏，消费者
编译时必须有 `WORKFLOW_USE_THREAD_IOSERVICE` 定义——通过
`package_info().cpp_info.defines` 导出（CMakeDeps 自动写入 target 编译选项），
否则消费者会 include 不存在的 IOService_linux.h（安装包只装 thread 版头）。

### 3. 上游测试的一处 STL 实现绑定（豁免，不打补丁）

`upstream_unittest.BasicPolicy`：一致性哈希测试硬编码 hash 值 4250947057
期望命中 8002 节点。vnode hash 用 `std::hash<std::string>`——libstdc++ 与
libc++ 实现不同 → OHOS 上 vnode 分布不同 → 稳定命中 8001。一致性哈希语义
本身正确（同 key 稳定映射，5 次运行结果一致），属测试对特定 STL 实现的
硬编码依赖，按平台差异豁免（配方 _run_upstream_tests 的 exempt 清单，
输出 [EXEMPT-PLATFORM] 标记）。

## 编译步骤

```bash
conan create . -pr:h ci/conan/profiles/ohos-aarch64 -pr:b ci/conan/profiles/ohos-aarch64 --build=missing
```

配方关键设置：
- `CMAKE_SYSTEM_NAME=Linux`（E092：CMake 无 HarmonyOS 平台模块；OHOS 内核是
  Linux，__linux__ 宏已定义，poller 走 epoll）
- `USE_THREAD_IOSERVICE=ON`（上述 AIO 问题）
- `KAFKA=n`（上游默认形态；其外部依赖部分不在制品仓）
- openssl 接线：CMakeDeps 前重写依赖 cpp_info 属性（cmake_file_name=OpenSSL
  + OpenSSL::SSL/OpenSSL::Crypto 目标名，同 i2pd 配方）——上游
  find_package(OpenSSL) 模块模式预期 OpenSSL::SSL 目标，直接 CMakeDeps 的
  小写 openssl::openssl 不匹配
- source() 删除 Bazel 的 BUILD/WORKSPACE 文件：与 conan cmake_layout 的
  build/ 目录在大小写不敏感文件系统（HMDFS）上同名冲突（NotADirectoryError）
- 上游测试：test/ 是独立 CMake project（EXCLUDE_FROM_ALL 目标），build() 内
  单独配置测试树（CMAKE_PREFIX_PATH 指向已安装包 + gtest 包 + openssl 模块
  变量 + LIBRT 显式路径）逐套件构建运行；运行期注入 workflow/openssl lib +
  工具链 libc++_shared.so 的 LD_LIBRARY_PATH
- OHOS 共享库签名（binary-sign-tool，同 brpc/gflags 配方）；libworkflow.so
  上游已设 VERSION/SOVERSION（DT_SONAME 正常），无需 patchelf

## 测试结果

- 上游 12 套件 38 TEST：37 通过 + 1 平台豁免（BasicPolicy，见上）
  - 全部本地可跑：redis/mysql/upstream/http 用内置 server + 127.0.0.1 回环，
    algo/graph/uriparser/resource/task/facilities 纯本地，dns 弱断言
- test_package：WFHttpServer(18811) + HTTP GET 回环 200 校验通过

## HMBS 标记

`HMBS_UPSTREAM_TEST_RESULT={"status": "passed", ..., "discovered": 38,
"executed": 39, "passed": 37, "failed": 0}`（executed 39 = 37 过 + 1 豁免 +
gtest 内 RUN_ALL_TESTS 尾断言计数；discovered 38 为 TEST() 注册数）

## 版本策略

R37：首次适配上游 1.1.0，版本号 `1.1.0` 无后缀。
---

**编译结束**: 2026-09-12 16:31
**最终状态**: published
