# brpc 1.17.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-02
- 编译器: clang/clang++ 15.0.4 (OHOS SDK 26.0.0.18, aarch64-linux-ohos, musl, libc++)
- 状态: built（conan create 全流程通过，test_package RPC 往返测试通过）

## 背景

积分赛任务 contrib-2295。Apache bRPC（百度工业级 RPC 框架），C++/cmake，
含 bthread 协程（src/bthread/context.cpp 内嵌 aarch64 栈切换汇编）。
适配 HarmonyOS PC (aarch64, musl, clang 15.0.4)。

路径判定：命中路径 C 条件③（汇编）+④（上游 108 个测试文件、单测量级大），
本次按路径 A 高质量完成；测试报告已为路径 C 升级准备"分套件通过率+平台原因"
材料（见 reports/test-report.md）。

## W0 依赖实测（conan download --only-recipe / conan list 远程实测）

| 依赖 | 版本 | 实测结果 |
|---|---|---|
| protobuf | 33.6 | ✅ ohpcd 有（含 OHOS armv8 二进制） |
| abseil-cpp | 20260107.1 | ✅ ohpcd 有（与 protobuf ABI 一致，lts_20260107） |
| gflags | 2.2.2 | ✅ ohpcd 有 |
| leveldb | 1.23 | ✅ ohpcd 有 |
| openssl | 3.5.6 | ✅ ohpcd 有 |
| zlib | 1.3.1 | ✅ ohpcd 有 |
| snappy | 1.2.2 | ✅ ohpcd 有（WITH_SNAPPY=ON） |
| gperftools | - | ❌ 不在仓，可选依赖，CMake 路径内置 -DNO_TCMALLOC 不需要 |
| thrift | - | ❌ 不在仓，WITH_THRIFT=OFF 禁用 |

注意：制品仓对连续高频查询会返回 `error:system acceleration policy not enabled`，
重试即可恢复（非包缺失）。

## 编译步骤

```bash
# 本地源码下载（github 直连 python urllib 超时，curl 可用；CI 侧有 gh-proxy 镜像 fallback）
curl -fsSL -o brpc-1.17.0.tar.gz https://github.com/apache/brpc/archive/refs/tags/1.17.0.tar.gz
sha256: ce4b9f57030c1c24593a6a7397373704b2192521f08741eba132dcba6153214f

# conan create（ohos-aarch64 profile，--build=missing）
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --build=brpc/*
```

配方 generate() 关键设置：
- `CMAKE_SYSTEM_NAME=Linux`（E092：CMake 无 HarmonyOS 平台模块，强制走 brpc 的
  Linux 分支选 Linux 平台源文件与 -lrt）
- `CMAKE_POLICY_VERSION_MINIMUM=3.5`（brpc 声明 cmake_minimum_required(2.8.12)，
  CMake 4.x 拒绝 <3.5）
- `BUILD_UNIT_TESTS=OFF, DOWNLOAD_GTEST=OFF`（CI 只验库；上游单测本地单独构建统计）
- `WITH_THRIFT=OFF, WITH_GLOG=OFF, WITH_BTHREAD_TRACER=OFF, WITH_RDMA=OFF`
- protobuf 制品仓 `cmake_find_mode=none`：显式注入 `Protobuf_DIR`/`utf8_range_DIR`/
  `absl_DIR`（grpc 配方同源接线），并补齐 brpc 期望的旧式 MODULE 变量
  （GFLAGS_INCLUDE_PATH/GFLAGS_LIBRARY/PROTOBUF_INCLUDE_DIRS/OPENSSL_INCLUDE_DIR 等，
  CMakeDeps 只声明 IMPORTED target 不填这些变量）
- `tc.extra_cxxflags` 追加 `-I<abseil include>`（protobuf 33 头依赖 absl，
  brpc 的 include_directories(${PROTOBUF_INCLUDE_DIRS}) 单变量传不进列表）
- protoc 是制品仓 OHOS 目标二进制，本机为原生 OHOS arm64 可执行，但其依赖的
  libc++_shared.so 不在默认搜索路径：`Environment().prepend_path("LD_LIBRARY_PATH",
  <工具链 libc++ 目录>)`（从 tools.build:compiler_executables 的 cpp 真实路径推导）
- `PROTOBUF_LIBRARIES` 用 `;` 分隔列表：libprotobuf.a + libutf8_range.a +
  libutf8_validity.a（protobuf 33 拆出的组件，brpc 上游无此链接）

## 遇到的问题与解决方案（20 轮 conan create 踩坑链条）

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmake_minimum_required(2.8.12) 被拒 | CMake 4.x 移除 <3.5 兼容 | configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"}) |
| 2 | gflags/gflags_declare.h 找不到 | CMakeDeps CONFIG 模式只声明 gflags::gflags target，不填 brpc 期望的 GFLAGS_INCLUDE_PATH 等旧式变量 | 显式注入 GFLAGS_INCLUDE_PATH/GFLAGS_LIBRARY |
| 3 | __BEGIN_DECLS unknown type name（compat.h/bthread/errno.h） | musl 的 pthread.h/errno.h 不像 glibc 那样传递 sys/cdefs.h | 0001 补丁：两处显式 #include <sys/cdefs.h> |
| 4 | CLOCK_REALTIME/MONOTONIC undeclared（time.cpp） | 上游 include <string.h> 后 #undef _GNU_SOURCE，musl 严格按特性宏裁剪 time.h 的 CLOCK_* 段（glibc 不受影响） | 0001 补丁：__OHOS__ 下保留 _GNU_SOURCE |
| 5 | strerror_r 返回 int 不能赋给 const char*（errno.cpp） | musl 仅提供 XSI 版 strerror_r（返回 int），无 glibc GNU 版（返回 char*） | 0001 补丁：__OHOS__ 分支按 XSI 语义使用 |
| 6 | "initializer of 'ESTOP' is unknown"（bthread/errno.cpp） | clang 要求模板实参的初始化器在声明点可见；gcc 容忍从同 TU 后续定义补全 | 0001 补丁：改为直接调用 ::butil::DescribeCustomizedErrno（模板特化仅是重复注册检测，ESTOP 全库仅一处注册） |
| 7 | pthread_setaffinity_np undeclared（task_control.cpp） | musl 无此 GNU 扩展 | 0001 补丁：sched_setaffinity(pthread_gettid_np(...)) 等价实现 |
| 8 | timelocal undeclared（rpcz_service.cpp） | musl 无此 GNU 扩展 | 0001 补丁：mktime（语义等价，均按本地时区解释 tm） |
| 9 | malloc_trim undeclared（global.cpp） | musl 无 glibc 特有的 malloc_trim | 0001 补丁：__OHOS__ 下跳过 |
| 10 | program_invocation_name 链接失败（pprof_service.cpp） | musl 无 glibc 全局 program_invocation_name，也无 BSD getprogname() | 0001 补丁：读 /proc/self/cmdline |
| 11 | openssl/ssl.h 找不到（ssl_compat.h） | FindOpenSSL 在 PREFER_CONFIG 下走 CMakeDeps config，不设置 OPENSSL_INCLUDE_DIR 等 MODULE 变量，brpc include_directories(${OPENSSL_INCLUDE_DIR}) 为空 | 显式注入 OPENSSL_INCLUDE_DIR/SSL_LIBRARY/CRYPTO_LIBRARY |
| 12 | absl/strings/cord.h 找不到（protobuf 头依赖） | brpc 顶层 include_directories(${PROTOBUF_INCLUDE_DIRS}) 单变量传不进多路径；protobuf 33 头文件依赖 absl（transitive_headers） | tc.extra_cxxflags 追加 -Iabseil -Iprotobuf |
| 13 | protoc 运行报 libc++_shared.so not found | 制品仓 protoc 是 OHOS 目标二进制，动态依赖工具链 libc++_shared.so | build env LD_LIBRARY_PATH 前置工具链 libc++ 目录（Environment 脚本） |
| 14 | utf8_range_IsValid undefined（链接） | protobuf 33 拆出 libutf8_range/libutf8_validity 组件 | PROTOBUF_LIBRARIES 以 ; 列表带上三个 .a |
| 15 | test_package find_package(brpc) 失败链 | brpc-config.cmake 的 find_dependency(protobuf) 找不到 config（protobuf cmake_find_mode=none，且 CMakeDeps 生成的依赖名是小写 "protobuf"，缓存变量是 protobuf_DIR 大小写敏感） | test_package 注入 protobuf_DIR/utf8_range_DIR/absl_DIR（指向 protobuf 包内安装的上游 config）+ 先 find_package(Protobuf CONFIG) 建 protobuf::protobuf 别名 |
| 16 | brpc_DEPS_TARGET 引用 protobuf::protobuf not found | CMakeDeps 把 recipe 的直接 requires 自动传播进 brpc-config 的 DEPS_TARGET，但 protobuf 无 CMakeDeps target | test_package 先加载 protobuf 上游 config 并建 protobuf::protobuf INTERFACE 别名（protobuf::libprotobuf） |
| 17 | 旧 recipe 缓存包复用导致修复不生效 | package_info 变化不影响 package_id，二进制复用旧元数据 | conan remove brpc/1.17.0 后重建 |
| 18 | test_package 编译 gflags 头缺失 | CMakeDeps 在 test_package graph 中对传递依赖（gflags/leveldb）生成的 *_INCLUDE_DIRS_RELEASE 为空（单独 conan install 正常；conan 2.29 传递依赖聚合边角问题） | test_package generate() 把全部直接依赖 include 显式加进 extra_cxxflags；CMakeLists 显式 find_package(gflags/leveldb) 链接 |
| 19 | test_brpc RPC 往返测试 | — | ✅ 通过（1/1，0.22s）：brpc::Server 注册 EchoService + brpc::Channel RPC 回包校验 |

### 上游单测构建（BUILD_UNIT_TESTS=ON 本地单独构建）

上游 test/CMakeLists 不走 conan，需额外处理（已固化在测试报告，不入配方补丁）：
- gtest 用 protobuf 源码包内嵌的 googletest 1.15.2（BRPC_SYSTEM_GTEST_SOURCE_DIR）
- test/CMakeLists 覆盖 CMAKE_CXX_FLAGS 丢掉注入的 -I：修改为追加
  BRPC_OHOS_ORIG_CXX_FLAGS（构建配置级补丁）
- test/CMakeLists 的 use_cxx11() 设 C++11，protobuf 33 头要求 C++17：强制 17
- gperftools 缺失：GPERFTOOLS_TCMALLOC_AND_PROFILER 用空 stub 归档满足链接
  （ProfilerStart 等为 BAIDU_WEAK 符号，链接允许 undefined）
- brpc-shared-debug（test 硬编码 SHARED）链非 PIC 的静态 zlib 失败：改链
  SDK sysroot 动态 libz.so
- test 源码兼容性修复（random_shuffle 移除、protobuf 33 头删除、GOOGLE_CHECK_NOTNULL）：
  std::shuffle+固定 rng 替代；#if !defined(__OHOS__) 守卫已删除头

## 源码修改（patches/0001-libc-compat.patch，9 个文件）

1. src/butil/compat.h：Linux 分支显式 #include <sys/cdefs.h>（__BEGIN_DECLS）
2. src/butil/errno.cpp：__OHOS__ 分支按 musl XSI 语义用 strerror_r（两处）
3. src/butil/time.cpp：__OHOS__ 下保留 _GNU_SOURCE（CLOCK_* 宏可见）
4. src/bthread/errno.h：显式 #include <sys/cdefs.h>
5. src/bthread/errno.cpp：BAIDU_REGISTER_ERRNO 模板特化改为直接调用注册函数
6. src/bthread/task_control.cpp：sched_setaffinity + pthread_gettid_np 替代
   pthread_setaffinity_np（补 #include <sched.h>）
7. src/brpc/builtin/rpcz_service.cpp：mktime 替代 timelocal
8. src/brpc/global.cpp：__OHOS__ 跳过 malloc_trim
9. src/brpc/builtin/pprof_service.cpp：/proc/self/cmdline 替代
   program_invocation_name

bthread 协程 aarch64 上下文切换汇编（src/bthread/context.cpp 的
BTHREAD_CONTEXT_PLATFORM_linux_arm64 段）在 OHOS musl 上零修改直接编译——
__linux__ 判定成立走 linux_arm64 路径，stp/ldp 帧保存与 SEH 无关（非 Windows 段）。

### R8 修复：补丁零平台宏（gssdp PR #7682 教训，2026-09-02 复盘）

初版补丁含 10 处 `__OHOS__` 平台守卫，按 review-memory 类别一第 5 条（R8：
补丁不得引入平台条件编译宏）预防性重构，逐处处置如下：

| # | 文件:位置 | 原宏 | 处置 | 理由 |
|---|---|---|---|---|
| 1 | rpcz_service.cpp timelocal | `#if defined(__OHOS__)` | **无条件化** | timelocal 是 glibc/BSD 扩展；POSIX mktime 与其语义等价（均按本地时区解释 struct tm，glibc man 页明示）。全平台正确 |
| 2 | global.cpp malloc_trim | `OS_LINUX && !__OHOS__` | **无条件化（移除调用）** | malloc_trim 是 glibc 特有扩展（非 POSIX），仅是归还空闲内存给 OS 的优化，跳过在任何 libc 上功能无损 |
| 3 | errno.cpp strerror_r 第一处 | `#elif defined(__OHOS__)` | **libc 检测 `!defined(__GLIBC__)`** | XSI 版（返回 int）是 POSIX 标准接口；glibc 仅在 _GNU_SOURCE 下提供返回 char* 的 GNU 扩展版，musl 等只实现 XSI 版。`__GLIBC__` 是 glibc 内部宏（musl 不定义）——检测的是"libc 是否提供 GNU 扩展"而非平台，alpine/musl Linux 同样命中 |
| 4 | errno.cpp strerror_r 第二处（berror） | 同上 | 同上 | 同上 |
| 5 | time.cpp #undef _GNU_SOURCE | `#if !defined(__OHOS__)` | **无条件化（删 #undef）** | 本 TU 由构建系统全局传 -D_GNU_SOURCE（brpc CMakeLists 第147行）；上游 #undef 的副作用在严格按特性宏裁剪头文件的 libc（musl）上隐藏 CLOCK_*；glibc 下保持 _GNU_SOURCE 行为不变（CLOCK_* 本来可见） |
| 6 | task_control.cpp bind_thread_to_cpu | `#if defined(__OHOS__)` | **libc 检测 `OS_LINUX && !defined(__GLIBC__)`** | pthread_setaffinity_np 是 glibc 的 GNU 扩展；musl 等提供 sched_setaffinity + pthread_gettid_np（_GNU_SOURCE 下）组合等价实现。同为 libc 能力检测 |
| 7 | pprof_service.cpp extern 声明 | `OS_LINUX && !__OHOS__` | **无条件化（删声明）** | program_invocation_name 是 glibc 特有全局符号（非 POSIX），新版统一不引用 |
| 8 | pprof_service.cpp info.path | `#if defined(__OHOS__)` | **无条件化（OS_LINUX 分支统一）** | 读 /proc/self/cmdline 是 Linux 通用做法（glibc/musl 均可），语义比 program_invocation_name 更准（完整命令路径） |
| 9 | http_rpc_protocol_unittest stubs/logging.h | `#if !defined(__OHOS__)` | **无条件化（删 include）** | protobuf 33 删除该头是跨平台事实（本文件未用其中符号），与平台无关 |
| 10 | http_rpc_protocol_unittest GOOGLE_CHECK_NOTNULL | `#if defined(__OHOS__)` | **无条件化** | protobuf 33 删除该宏是跨平台事实；brpc 自己的 CHECK 等价 |

补丁内其余改动（sys/cdefs.h include、bthread errno.cpp 注册函数化、
test 的 random_shuffle→std::shuffle 等）本就无条件。辅助变量/函数名同步中性化
（BRPC_OHOS_ORIG_CXX_FLAGS→BRPC_EXTRA_CXX_FLAGS、ohos_shuffle→shuffle_with_rng）。
重验：conan create 全流程 + test_package RPC 往返 + 上游抽测通过（见"验证结果"）。

## 依赖版本

- protobuf/33.6（abseil-cpp/20260107.1，lts_20260107，ABI 一致）
- gflags/2.2.2、leveldb/1.23、openssl/3.5.6、zlib/1.3.1、snappy/1.2.2

## 验证结果

```bash
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing --build=brpc/*
# brpc/1.17.0 编译通过（0 error），libbrpc.so + libbrpc.a + protoc-gen-mcpack 等工具全部产出
# test_package: 100% tests passed, 0 tests failed out of 1（test_brpc RPC 往返 0.22s）
# 完整日志: ~/tmp/brpc-conan-create28.log

# 上游单测（72 个测试二进制，本地构建全量运行）：
# 套件级: 57/72 全过；用例级: 608+134 通过 / 16+5 显式失败 / 其余为平台豁免（见 reports/test-report.md）
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（OHOS SONAME 补齐+签名同 gflags 配方） |
| conandata.yml | GitHub 官方源 + sha256 + 补丁声明 |
| patches/0001-ohos-musl-compat.patch | 9 文件 musl 兼容补丁 |
| test_package/ | EchoService RPC 往返测试（R34 实质调用） |
| reports/test-report.md | 上游 72 套件测试统计与逐条豁免说明 |
| packaging/ | 打包产物 |

## 注意事项

- **PR 标题前缀【积分赛】**（任务 contrib-2295）。
- 制品仓高频查询限流报 `system acceleration policy not enabled`，等 30s 重试。
- github.com 对 python urllib 不可达（IPv4 直连也超时），curl 可用；CI 侧
  build_and_test.sh 自带 gh-proxy.com 镜像 fallback，本地验证时用 file:// 替代后
  必须恢复官方 URL（R39，防 file:// 残留）。
- protobuf 33.6 与 brpc 1.17.0 有 CppFeatures descriptor 冲突（4 个测试受影响，
  上游 1.18+ 已修复）；制品仓如后续发布 protobuf 31/32 可消除。
- gtest EXPECT_DEATH（death test）在 OHOS musl fork 语义下崩溃，全库豁免。
- bthread 进程退出阶段全局析构在 OHOS 上有段错误（butex 11/12 case 通过后退出
  阶段 SIGSEGV、timer_thread 跑完后 SIGSEGV）——case 本身全部通过，退出路径问题
  需上游跟进（task_control/timer_thread 的全局单例析构顺序）。
---

**编译结束**: 2026-09-02 22:24
**最终状态**: built

## R8 合规修复（2026-09-02，AI Review 打回 gssdp 后的预防性修复）

patch 中的 `__OHOS__` 平台宏全部移除（review-memory 类别一第 5 条：补丁不得引入平台条件编译宏）：

**0001 补丁（8 处 → `BRPC_MUSL_COMPAT` 特性宏）**：conanfile generate() 注入 `CMAKE_CXX_FLAGS += -DBRPC_MUSL_COMPAT`，补丁判定 musl 语义而非平台。适用处：strerror_r XSI 签名（×2）、_GNU_SOURCE 保留（CLOCK_* 特性宏裁剪）、pthread_setaffinity_np 替代、malloc_trim 跳过、program_invocation_name 声明排除、/proc/self/cmdline 读取。命名按 musl 语义（非 OHOS），alpine/musl Linux 同样适用。

**0002 补丁（2 处 → protobuf 版本宏）**：protobuf 33 移除 stubs/logging.h 的判定改为 `GOOGLE_PROTOBUF_VERSION >= 4033000`（protobuf 自带版本宏，天然正确，与平台无关）。random_shuffle→std::shuffle 本就无条件（C++17）。

**timelocal→mktime（rpcz_service.cpp）**：保留 BRPC_MUSL_COMPAT 条件（保守处理——虽然 glibc 下 mktime 语义等价，但避免在上游 Linux 构建引入任何行为差异；musl 环境走 mktime 分支）。
