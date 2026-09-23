# bctoolbox 5.3.115 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-11（首版 2026-09-05；本轮接入上游 tester 后重建）
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos) + GNU Make 4.4.1 + CMake 4.1.2
- Conan: 2.29.1 (os=OHOS profile `ci/conan/profiles/ohos-aarch64`)
- 并行度: 本任务所有构建显式 `-c tools.build:jobs=2`。原因：容器 `/proc/stat` 报 20 个 CPU 而 affinity 只有 8 个，
  conan 默认 `tools.build:jobs` 取 `os.cpu_count()`=20（实测构建行 `RUN: cmake --build ... -- -j20`），
  在 8 CPU 上属 2.5x 超订，会互相拖慢并抬高内存峰值。
  ⚠️ 更正（原判断已实测证伪）：本任务早前把当天 08:25–09:08 的设备级内存耗尽归因于这个 20 路并行，**不成立**——
  用同一条编译命令逐 TU 实测峰值 RSS 仅 `cipher.c 72.7 / bignum.c 74.4 / ssl_tls.c 78.8 / x509_crt.c 78.8 / entropy.c 78.8 MB`，
  20 路满并发约 1.5–2 GB，无法解释 32 GB 设备出现 `MemFree 812 MB` + 约 18 GB swap；
  同窗口另一会话（debfoster 2.8，小型 autotools 包）在我方构建结束后仍复现同签名 `can't fork - try again`，
  且 `/proc` 下 140/212 个进程属其他用户（多租户共享设备），故**设备级 OOM 无法归因到本任务**。
  固定低并发的口径保留，理由改为"共享设备并发卫生 + 避免 2.5x 超订"。
- 状态: built

## 编译步骤

原生探索（设备端真机构建，任务源码副本）:

```bash
cmake -S . -B build-shared -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX=<install> -DBUILD_SHARED_LIBS=ON \
  -DENABLE_TESTS_COMPONENT=ON -DENABLE_UNIT_TESTS=ON \
  -DENABLE_MBEDTLS=OFF -DENABLE_DECAF=OFF
make -C build-shared -j1 && make -C build-shared install
```

Conan 构建（测试组件打开，上游 tester 在 `build()` 内真实执行）:

```bash
conan create archives/b/bctoolbox/5.3.115 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  -c tools.build:jobs=2 --build=missing --user=ohpcd --channel=stable
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 消费者启动报 `Error relocating libbctoolbox.so: bctbx_clean: symbol not found` | `vfs.c`（核心必编文件）引用 `bctbx_clean`，而其定义仅在 mbedtls 后端源文件（`crypto/mbedtls.c`/`mbedtls-v2.c`）；关闭 mbedtls 时无人提供定义 | 补丁 `0001-src-utils-port.c.patch`：在 `port.c` 用 `#if !defined(HAVE_MBEDTLS)` 提供与上游 pre-mbedtls-2.10 分支等价的 volatile 零化实现（上游自有特性宏门控，非 `__OHOS__` 平台条件编译） |
| 2 | `-DENABLE_MBEDTLS=ON` + mbedtls/4.1.0 编译失败：`mbedtls/ctr_drbg.h: No such file or directory` | bctoolbox 5.3 的 mbedtls 包装器只支持 v2/v3 API；mbedtls 4 已将 ctr_drbg 等模块私有化移除；上游 CMake 亦明示 "requires v2 or v3" | `ENABLE_MBEDTLS=OFF`（上游软可选配置；ohpcd 仅有 mbedtls/4.1.0，无 v2/v3 可用）。全集 35 用例改由测试专用 mbedtls 3.6.6 源码包验证（见下） |
| 3 | `ENABLE_TESTS_COMPONENT=ON` 时 `find_package(BCUnit 3.0.2 REQUIRED)` 失败 | 上游硬性要求 BCUnit 3.0.2；bcunit 当时未发布 | ohpcd 已发布 `bcunit/5.3.113`（BC 仓按 linphone SDK 锁步打 tag，项目内版本号仍写 3.0.2），改用 `test_requires("bcunit/5.3.113")` 并把测试组件打开 |
| 4 | 打开测试后 `Could not find a configuration file for package "BCUnit" that is compatible with requested version "3.0.2"`（found 5.3.113） | CMakeDeps 默认 `SameMajorVersion`：请求 3.0.2 时 5.x 不被接受；而 bcunit 的 CMake 项目版本号长期冻结在 "3.0.2"（5.3.113 内容正是满足并扩展 3.0.2 API 的那份） | `deps.set_property("bcunit","cmake_config_version_compat","AnyNewerVersion")` |
| 5 | 打开测试后编译 `src/tester.c` 报 `unused parameter 'tag_name'/'handler' [-Werror]` | `CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON`（conan toolchain 固定写入）使上游 `cmake/FindBCUnit.cmake` 成死代码，它本该产出的 `HAVE_CU_GET_SUITE`/`HAVE_CU_SET_TRACE_HANDLER` 等 config.h 宏无人设置，相关代码路径被编译掉后参数变成未使用 | 配方 `generate()` 预置 `BCUnit_TARGET=bcunit::bcunit`、`HAVE_CU_GET_SUITE=TRUE`、`HAVE_CU_SET_TRACE_HANDLER=TRUE`、`HAVE_CU_CURSES=FALSE`（与 bcunit/5.3.113 实际符号一致：有 `CU_get_suite`/`CU_set_trace_handler`，无 curses） |
| 6 | tester 运行到 `Utils / Addrinfo sort` 段 `Signal 11`，faultlog `SIGSEGV(SEGV_MAPERR)@0x20` | `bctbx_freeaddrinfo()` 第一行就解引用 `res->ai_canonname`，而该用例在 `res1->ai_next` 为空时合法地把 NULL 交给它（POSIX/glibc 的 `freeaddrinfo(NULL)` 是 no-op） | 补丁 `0002-src-utils-port.c-freeaddrinfo-null.patch`：入口加 NULL 直接返回（llvm-symbolizer 定位 `bctbx_freeaddrinfo ← bctbx_addrinfo_sort_test`） |
| 7 | 同上用例在 OHOS 上断言不成立 | 该用例的 IPv6 项取自 `bctbx_name_to_addrinfo(AF_INET6, "sip3.linphone.org")`；无 IPv6 连通性的主机只拿到 A 记录（本机为 fake-IP `198.18.8.255`），得到单个 v4-mapped 项，用例的「IPv4 < v4-mapped < 纯 IPv6」排序断言失去前提 | 补丁 `0003-tester-port.c-addrinfo-sort.patch`：IPv6 项改用 IANA 文档地址 `2001:db8::1`（排序断言与覆盖面不变，去掉外部 DNS/IPv6 依赖） |
| 8 | 每套件跑完（Run Summary 之前）必然 `Signal 11`，rc=139 | 上游 `src/tester.c` 在 `__linux__` 且非 glibc 时走 `#else` 分支调用 `mallinfo()`；OHOS libc 只在 API≥20 声明该符号，实测「调用返回后进程即崩溃」（独立探针复现 rc=139） | 补丁 `0004-src-tester.c-mallinfo-glibc-only.patch`：把两个 `mallinfo()` 调用点（`--max-alloc` 检查与收尾统计）限制在 glibc（`__GLIBC_PREREQ`）；非 glibc 不再调用该设施 |
| 9 | 全特性验证时 `src/crypto/mbedtls.cc` 报 `undeclared identifier 'mbedtls_threading_set_alt'` 等 4 处 | `mbedtls.cc` 在 `MBEDTLS_VERSION_NUMBER >= 0x03060000`（即 mbedtls ≥ 3.6）时无条件定义 `BCTBX_USE_MBEDTLS_PSA` 并调用 ALT 线程 API；这些声明只在 mbedtls 开启 `MBEDTLS_THREADING_C` 时可见，而 mbedtls 3.6 默认把 threading 注释掉 | 测试专用 mbedtls 包启用 `MBEDTLS_THREADING_C` + `MBEDTLS_THREADING_ALT` 并提供 `include/mbedtls/threading_alt.h`（`typedef void *mbedtls_threading_mutex_t;`，与 BC 定制 mbedtls 一致）；库与消费者必须同一配置（线程开关改变上下文结构体布局） |
| 10 | static 包被纯 C 消费者链接报 `undefined symbol: std::length_error / __cxa_throw / vtable` | 库由 C++17 对象构成但 API 为 C 形态；static 归档消费时 C 驱动不链 C++ 运行时（知识图谱 E247 同模式） | 配方 `package_info()` 在 `shared=False` 时声明 `cpp_info.system_libs=["c++"]`，消费者侧由 Conan 传递 `-lc++`；shared=True 时 .so 已带 `DT_NEEDED libc++_shared.so` 无需声明。设备实测：同一 static 产物加 `-lc++` 后链接并运行 exit=0 |

## 源码修改

- `patches/0001-src-utils-port.c.patch` — `src/utils/port.c`：`#if !defined(HAVE_MBEDTLS)` 门控的 `bctbx_clean` 零化兜底（+14 行；等价物为上游 v2.10 前的同名实现）。
- `patches/0002-src-utils-port.c-freeaddrinfo-null.patch` — `src/utils/port.c`：`bctbx_freeaddrinfo()` 接受 NULL 列表（POSIX `freeaddrinfo(NULL)` 契约）。
- `patches/0003-tester-port.c-addrinfo-sort.patch` — `tester/port.c`：`Addrinfo sort` 用例的 IPv6 项改用文档地址字面量，去掉外部 DNS/IPv6 依赖（断言不变）。
- `patches/0004-src-tester.c-mallinfo-glibc-only.patch` — `src/tester.c`：`mallinfo()`/`mallinfo2()` 仅在 glibc 调用（OHOS libc 该符号不可用且调用即崩）。

四个补丁均无 `__OHOS__` 平台条件编译：0001 用上游特性宏、0003 是测试数据、0004 用 libc 族判定；每次 `conan create` 日志均有对应 `Apply patch` 行。

## 依赖版本

- `bcunit/5.3.113`（ohpcd 已发布）— `test_requires`：只服务上游 tester，不进入消费方依赖链（消费者图内为 `Skipped binaries`）。上游要求 `BCUnit 3.0.2` 是「内容时代」而非包版本（见问题#3/#4）。
- mbedtls：交付包**不依赖**（`ENABLE_MBEDTLS=OFF`）。全集 35 用例中的 15 个 crypto/encrypted_vfs 用例在
  「测试专用 mbedtls 3.6.6 源码包」的验证配置下执行，证据见 `reports/upstream-test-full-feature.md`。
- decaf：未发布于 ohpcd，`ENABLE_DECAF=OFF`（上游软可选）。

## 验证结果

```bash
# 原生共享库 + C 消费者（list + logging）
LD_LIBRARY_PATH=<install>/lib ./consumer   # exit=0: list size=2 first=hello / consumer log works
# C++ 消费者（regex + BctbxException）
LD_LIBRARY_PATH=<install>/lib ./consumer-cxx  # exit=0: regex=1 exception=1
# 符号核验
nm -D --defined-only libbctoolbox.so | grep -w bctbx_clean   # 已导出
nm -D -u libbctoolbox.so | grep -w bctbx_clean               # 无输出（无未定义符号）
```

上游 tester（`build()` 内真实执行，退出码决定包构建成败）：

| 配置 | suites | tests | passed | failed | asserts |
|------|--------|-------|--------|--------|---------|
| 交付配置 `ENABLE_MBEDTLS=OFF` | 6 | 20 | 20 | 0 | 779 |
| 全特性验证配置 `ENABLE_MBEDTLS=ON` + 测试专用 mbedtls 3.6.6 | 8 | 35 | 35 | 0 | 103688 |

分母 35 = 上游注册用例总数（`grep -oE "TEST_NO_TAG|TEST_ONE_TAG|TEST_TWO_TAG" tester/*.c tester/*.cc | wc -l`），
与审方数法一致；分布与两套配置的逐项结果见 `test_package/MANIFEST.yml`。

Conan 链路验证（同一 SHA，清缓存后 `conan create` + `test_package` 6 项断言全 PASS、L2 消费者实测、
L4 NX/PIE/RELRO、L5 产物基线）见 `reports/` 下 conan-verify/conan-create 日志。

## 交付物

| 文件 | 说明 |
|------|------|
| include/bctoolbox/*.h(hh) | 公共头文件 |
| lib/libbctoolbox.a（shared=False）或 lib/libbctoolbox.so（shared=True） | 库产物 |
| lib/pkgconfig/bctoolbox.pc | pkg-config 描述文件 |

`libbctoolbox-tester.a`/`bctoolbox-tester.pc` 是 `ENABLE_TESTS_COMPONENT=ON` 的上游安装产物（测试辅助库）；
tester 可执行文件已在 `package()` 中剔除（构建期验证产物，非交付物）。

## 注意事项

- 上游 tester 的全部 35 个用例均已真实编译执行（20 个在交付配置内，15 个 mbedtls 门控用例在测试专用
  mbedtls 3.6.6 的验证配置内），全集 35/35 PASS、0 FAIL、0 SKIP。
- 本包无命令行工具产物（tester 可执行文件已剔除），按 PF8/R38 纯库包不提供 commands.json。
- mbedtls 4.x 与 bctoolbox 5.3 不兼容（首错 `mbedtls/ctr_drbg.h` 缺失）；若 ohpcd 后续发布 v2/v3 版
  mbedtls（必须带 `MBEDTLS_THREADING_C`+`MBEDTLS_THREADING_ALT`，见问题#9），可把 `ENABLE_MBEDTLS`
  置 ON 并加 `requires`，届时交付包自身即可跑满 35/35。
- 运行并发固定 `-c tools.build:jobs=2`：本设备 conan 默认取 20（见「编译环境」），高并发会打挂整机。

## 发现与知识

- ✅ 发现与知识#1：bctoolbox 核心（vfs.c）引用 bctbx_clean，但上游只在 mbedtls 后端源文件提供定义；无后端构建的 .so 携带未定义符号，消费者启动即 relocation 失败——需特性宏门控的兜底定义（同问题#1）。
- ✅ 发现与知识#2：bctoolbox 5.3 mbedtls 包装器仅兼容 v2/v3 API，mbedtls 4 移除 ctr_drbg.h 直接致命；依赖方遇到 v4-only registry 时应关闭后端而非强配（同问题#2）。
- ✅ 发现与知识#3：ENABLE_TESTS_COMPONENT 在上游是硬性引入 BCUnit 3.0.2 的开关；BC 系软件仓（bcunit）按 linphone SDK 锁步打 tag，仓内项目版本号长期冻结在 3.0.2，故「版本」须按内容时代选（5.3.113 才含 `CU_Suite.pUserData`/`CU_automated_enable_partial_junit`，3.0.2 tag 内容缺这些 API）（同问题#3）。
- ✅ 发现与知识#4：CMakeDeps 默认 `SameMajorVersion`，当依赖包 ref 版本与其内部项目版本号跨大版本时（bcunit 5.3.113 vs 请求 3.0.2）必须 `set_property(dep,"cmake_config_version_compat","AnyNewerVersion")`，否则 CONFIG 模式拒绝该 config 文件、回退 MODULE 模式并在上游 Find 模块里二次 find_package 报错（同问题#4）。
- ✅ 发现与知识#5：`conan_toolchain.cmake` 固定 `CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON`，上游自带 `FindXxx.cmake` 变成死代码，它负责设置的 `<Xxx>_TARGET` 与特性宏（写进 config.h 的 `HAVE_*`）全部落空——消费方必须在 `generate()` 里预置这些变量，而不是去补丁 Find 模块（死代码）（同问题#5）。
- ✅ 发现与知识#6：CMake 4.1.2 无 HarmonyOS 平台文件时打印 "System is unknown to cmake" 但 check_include_file/check_library_exists 探测仍正确工作（execinfo.h/rt/dl 全部检出），不构成阻塞。
- ✅ 发现与知识#7：C 形态 API 的 C++ 静态库必须声明 `cpp_info.system_libs=["c++"]`，否则纯 C 消费者链接 static 归档时在 std::length_error/__cxa_throw/vtable 上失败（E247 同模式）；shared 包因 .so 自带 libc++_shared 依赖无需声明（同问题#10）。
- ✅ 发现与知识#8：上游 tester 框架的 `bctbx_freeaddrinfo()` 不遵守 `freeaddrinfo(NULL)` 契约（首行解引用 `ai_canonname`），其自带用例会合法地传 NULL——包装类 API 的 NULL 语义必须与底层 libc 对齐（同问题#6）。
- ✅ 发现与知识#9：`mallinfo()`/`mallinfo2()` 是 glibc 设施；OHOS libc 头文件按 API≥20 声明但运行期不可用，调用后进程必崩（本机独立探针 rc=139），上游 `#ifdef __linux__` 的宽判据会在 OHOS 上引入该崩溃——libc 专属设施应按 libc 族（`__GLIBC_PREREQ`）而非 OS 判定（同问题#8）。
- ✅ 发现与知识#10：依赖源码测试若依赖外网解析（本例 `bctbx_name_to_addrinfo` 取 `sip3.linphone.org` 的 IPv6 记录），在无 IPv6 的设备上断言前提消失甚至空指针崩溃；上游用例的地址来源应改为保留字面量，避免环境依赖（同问题#7）。
- ✅ 发现与知识#11：bctoolbox ≥5.3 在 mbedtls ≥3.6 上走 PSA + ALT 线程路径（`src/crypto/mbedtls.cc` 按 `0x03060000` 门控），要求 mbedtls 以 `MBEDTLS_THREADING_C`+`MBEDTLS_THREADING_ALT` 构建；mbedtls 3.6 默认关闭 threading，vanilla 3.6.6 直接编译失败，且线程开关会改变 mbedtls 上下文结构体布局，库与消费者必须同配置（同问题#9）。
- ✅ 发现与知识#12：容器 `/proc/stat` 报 20 CPU 而 affinity 仅 8，conan 默认 `tools.build:jobs` 取 `os.cpu_count()`=20（8 CPU 上 2.5x 超订）；但**逐 TU 实测峰值 RSS 仅 ≈79 MB，20 路约 1.5–2 GB，不足以造成设备级 OOM**——同窗口另有其他用户/会话（`/proc` 下 140/212 进程不可读；debfoster 2.8 在我方构建结束后仍报 `can't fork - try again`），故共享设备上仍应显式限制 `-c tools.build:jobs`，但口径是"并发卫生与超订"，不是"本包构建会打挂设备"（同「编译环境」更正段）。
- ✅ 发现与知识#13：`build()` 内执行自建测试程序时，工作目录必须是该可执行文件所在目录。bctoolbox 的 shared 构建把依赖记成**相对 `DT_NEEDED`**（实测 `../src/libbctoolbox.so`、`../src/libbctoolbox-tester.so`），而加载器把含 `/` 的 DT_NEEDED 当字面路径相对**当前工作目录**解析（不走 LD_LIBRARY_PATH）——从 build 根目录启动时报 `Error loading shared library ../src/libbctoolbox.so` 并伴随整串 `Error relocating: symbol not found`（容易被误判为符号缺失），改 `cwd=os.path.dirname(tester)` 后 shared 形态 20/20 PASS。
