# libmsquic 2.5.7 OHOS 适配 notes

## 上游信息
- 名称：libmsquic（Microsoft MsQuic，IETF QUIC 协议 C 实现）
- 版本：2.5.7（tag v2.5.7，commit 801b0e958f3e33e9998766c3371c1ca348254650）
- 仓库：https://github.com/microsoft/msquic
- 许可证：MIT
- 源码包：https://github.com/microsoft/msquic/archive/refs/tags/v2.5.7.tar.gz（8138248 字节，sha256 ef447e3f…99b9e5，Windows 本机下载实测）
- 构建系统：CMake（最低 3.16，Linux 走 Unix Makefiles；PowerShell 脚本仅为封装，配方直接调 CMake）

## 上游测试清点（适配前）
- 来源：CMakeLists.txt `option(QUIC_BUILD_TEST)` + docs/TEST.md + src 目录结构
- `src/core/unittest` → msquiccoretest，文档示例 208 用例（gtest）
- `src/platform/unittest` → msquicplatformtest，文档示例 66 用例（gtest）
- `src/test` → msquictest，文档示例 1681 用例（gtest，端到端，需 UDP 回环与自签证书）
- 合计约 1955 用例；确切 discovered/executed/passed 以真机 `ctest --output-on-failure` 输出为准，本轮不猜测
- 证伪计划：检查 ctest 输出非空且 LastTest.log 存在；若出现 0 测试或全跳过，按跳过计，不计通过

## 依赖检查（W0/R36）
- 本配方零外部 requires：TLS 走 vendored quictls（OpenSSL 分支，随源码构建），日志关闭，不依赖制品仓任何包
- 构建工具：cmake/make/ninja/python3 由 HMBS 统一注入 PATH；perl 由真机提供（quictls Configure 需要，openssl 配方同款假设）
- 无需 tool_requires；`conan download` 无待验证依赖

## 子模块处理（tarball 不含 submodule）
GitHub tag tarball 不含 `submodules/*`，配方在 `source()` 阶段从官方 GitHub 按 v2.5.7 pinned commit 重取：
- `submodules/clog` ← microsoft/CLOG@f1341710（110083 字节，sha256 d5c038c8…5aef2db）
- `submodules/quictls` ← quictls/openssl@ff36838b（15863716 字节，sha256 0419330d…2c9e4ed01e0150）
- `submodules/googletest` ← google/googletest@90a41521（886622 字节，sha256 8fab9c25…f361c5d4f）
- `submodules/xdp-for-windows` 不取：仅 Windows/XDP 用，Linux aarch64 强制关闭
- 全部为官方上游仓库 tag/commit 归档，校验值已在 Windows 本机实测并硬编码

## CMake 配置
- `QUIC_BUILD_SHARED` 跟随 `options.shared`（默认 False，静态单体库，避开 OHOS 共享库签名链）
- `QUIC_BUILD_TOOLS=OFF`、`QUIC_BUILD_PERF=OFF`：仅库+测试，控制真机耗时
- `QUIC_BUILD_TEST=ON`：构建三套 gtest 二进制，`build()` 末尾跑 `ctest --output-on-failure`
- `QUIC_ENABLE_LOGGING=OFF`：Linux 默认 lttng 在 OHOS 无对应开发包，关闭后走 STUB 后端
- `QUIC_TLS_LIB=quictls` + `QUIC_USE_SYSTEM_LIBCRYPTO=OFF`：自包含，不吃系统 libcrypto
- `QUIC_LINUX_XDP_ENABLED=OFF`：上游 XDP 仅 x64，aarch64 强制关
- `QUIC_EMBED_GIT_HASH=OFF`：tarball 无 .git，关掉 git 哈希嵌入
- `QUIC_SOURCE_LINK/QUIC_PDBALTPATH/QUIC_STATIC_LINK_*=OFF`：Windows 专用，显式关以免交叉影响
- OHOS shared=ON 时沿用 libcurl 式 rpath/soname 修正与 objcopy/sign 签名；默认静态路径不触发

## 平台风险（待真机验证）
1. `CMAKE_SYSTEM_NAME=HarmonyOS` 时上游 `if(WIN32)/elseif(APPLE)/elseif(UNIX)` 可能落空导致 CX_PLATFORM 为空；若真机报此错，下一轮加 portability 补丁把 HarmonyOS/OHOS 映射到 linux（补丁不含 __OHOS__，符合 PF5）
2. Linux datapath 特性探测（UDP_SEGMENT/sendmmsg/SO_ATTACH_REUSEPORT_CBPF）在 OHOS 缺失时上游仅降级打印 STATUS，不致命；`QUIC_CI` 未开，不会因此 FATAL
3. `msquic_posix.h` 要求 `__linux__`；OHOS clang 若未定义会 `#error Unsupported Platform`，待真机确认
4. msquictest 1681 集成用例需 UDP 回环与证书，若真机受限失败，下一轮按实际失败分类处理（先补低成本依赖，不静默跳过）

## test_package（R34）
- `test_msquic.c` 真实调用 API：`MsQuicOpen2` 校验 API 表 + `RegistrationOpen/Close` 校验线程/内存路径
- 3 种跑法：`open` / `registration` / `all`；`all` 跑 2 用例并打印 `HMBS_TEST_PACKAGE_RESULT`（discovered=2）
- `test_package/conanfile.py` 在 OHOS 用 bash 包裹执行（libcurl 同款，/system/bin/sh 不能直接 exec ELF），随后从 `package/res/hmbs_upstream.json` 复发 `HMBS_UPSTREAM_TEST_RESULT`（ali 0.8.0 持久化模式，防缓存命中丢失证据）

## 证据门禁（待真机 evidence 轮填写）
- `HMBS_TEST_PACKAGE_RESULT`：由 `test_msquic all` 真实计数打印，discovered=2
- `HMBS_UPSTREAM_TEST_RESULT`：由 `build()` 内 `ctest --output-on-failure` 解析（`X% tests passed, Y failed out of Z`），双通道输出（print + self.output.info）并持久化 `build_folder/hmbs_upstream.json` → `package/res/hmbs_upstream.json`
- 本轮未跑真机，PR 草稿中通过率写“待真机实测”，不编数字

## 验证状态
- 本机：仅完成配方静态编写与 `git status` 自检，未跑 conan（按守则，真机外不跑 conan）
- 真机：待 HMBS 后台 `conan create` 全量验证（编译 + test_package + ctest）
- 本轮保持未提交，不 commit/push，不建 PR

## 真机失败追踪（预检轮）
- 2026-09-17 compile 失败 `System is unknown to cmake / Platform/HarmonyOS`：Conan 把 OHOS 映射为
  CMAKE_SYSTEM_NAME=HarmonyOS，stock CMake 4.4.3 无此平台模块，`try_compile` 链接可执行文件失败被误报为
  编译器损坏。首轮 `CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY` 未补平台模块，同错复现，无效。
- 上轮改为 E092 强制 `CMAKE_SYSTEM_NAME=Linux` + `PROCESSOR=aarch64`（主包/test_package 一致），
  “System unknown”消失，但 `project()` 仍报 compiler identification unknown；同轮 HMBS 平台诊断给出
  `[readonly_tmp]`（/tmp 只读，preflight.sh 自身 mktemp /tmp 也失败），而 clang 中间文件默认落 /tmp。
- 本轮在 Linux 覆盖基础上追加最小文件系统适配：新增 `_hmbs_writable_tmp()`，优先复用 HMBS 注入的
  任务独立 TMPDIR/TMP/TEMP（可写探测），不可用时回退 `build_folder/hmbs-tmp`；`generate()`/`build()`
  均导出该目录（test_package 的 `build()` 同理）。不碰测试口径，不处理诊断之外的子能力。
- 真机已消费 TMPDIR 修复（日志出现 `hmbs writable tmpdir: .../runtime/libmsquic-2.5.7/tmp`）但
  `project()` 仍报 compiler identification unknown，证伪“/tmp 是编译器自检失败主因”。
  重新比对：bruteforce-luks 第 21 轮笔记实证 `CMakeToolchain` 把 `CMAKE_C_COMPILER` 钉死在
  profile 绝对路径 `/data/service/hnp/bin/clang`，该路径在部分预检客户端不可用，
  cmake 首个 `project()` 即校验该二进制且不受 CC 环境变量影响；lz4 草稿亦记录真机工具链已迁移至
  `/storage/.../usr/local/bin`（本轮 HMBS_BUILD_TOOLS 的 cmake/make/ninja 同在此目录）。
  前两轮（STATIC_LIBRARY、TMPDIR）均够不着该校验点，故同错复现。
- 本轮改走 cvector/1.0.4.1 先例的 stale-toolchain guard（与前两轮不同路线）：主包/test_package
  各加 `_compiler_executable()`（conf 绝对路径经 isfile+可执行校验才采用，否则按
  CC/HMBS_CC、CXX/HMBS_CXX 环境与 PATH 中 clang/clang++ 顺序回退并 warning），OHOS 下写入
  `tc.cache_variables["CMAKE_C_COMPILER/CMAKE_CXX_COMPILER"]`，`generate()` 后再用
  `_patch_cmake_toolchain_compilers()` 对 `conan_toolchain.cmake` 做 replace_in_file 兜底
  （clang++ 先于 clang：c 路径是 cpp 路径的子串）。Linux 覆盖与 TMPDIR 转发保留。
- 2026-09-17 新失败域（第 3 策略周期）：顶层 `project()` 已通过（日志 `-- Configuring done (10.7s)`、
  `QUIC Platform: linux`），前三轮 project() 级假设（STATIC_LIBRARY/Linux 平台名/TMPDIR/编译器回退）
  已被证伪为非当前阻塞点；新断点在 vendored quictls：`Configuring OpenSSL version 3.1.7+quic
  for target HarmonyOS` 后 `submodules/quictls/Makefile Error 1`。上游 `submodules/CMakeLists.txt`
  在 CX_PLATFORM=linux 且 CMAKE_TARGET_ARCHITECTURE 未置时走 `config CC=...` 自动探测，
  OHOS clang 被误判为 HarmonyOS（quictls 无此 target，Configure 打印目标列表后非零退出、无 Makefile）。
  本轮换路线：不再动顶层编译器判定，改为 quictls 目标强制——`source()` 内对
  `submodules/CMakeLists.txt` 做最小补丁（`Configure linux-aarch64 CC=${CMAKE_C_COMPILER}`；
  fallback 分支按 CMAKE_SYSTEM_PROCESSOR 匹配 aarch64/arm64 时同样强制，参考 openssl/3.5.8.1
  显式 linux-aarch64+CC 先例），`generate()` OHOS 下新增 `CMAKE_TARGET_ARCHITECTURE=arm64`
  以命中上游已有交叉分支。TMPDIR 转发与编译器回退保留；`[readonly_tmp]` 仅为 preflight 脚本
  自身 mktemp 失败，配方已复用 HMBS 注入 TMPDIR，不另做文件系统改动。
- 2026-09-17 quictls 修复生效（`Configure;linux-aarch64;CC=...harmonybrew/bin/clang`、`Configuring done (10.1s)`，
  构建推进至 47-48%），前次 quictls-target 策略有效故不再重复；新断点在
  `src/platform/platform_posix.c:710 pthread_setaffinity_np隐式声明-Werror`。上游该文件首处
  attr 亲和已用 `#ifdef __GLIBC__` 包裹，但创建后 `pthread_setaffinity_np` 块仅判
  `#if !defined(__ANDROID__)`，OHOS（musl，非 Android 非 glibc）仍命中，而 musl 头文件未暴露该
  GNU 扩展。亲和仅 best-effort（失败只记日志），本轮换路线：`source()` 对该文件做一行最小补丁
  `#if !defined(__ANDROID__) && defined(__GLIBC__)`，与既有 attr 模式一致，线程创建仍成功、无亲和，
  同 Darwin 行为；不删断言、不跳过测试。
- 2026-09-17 亲和修复生效（构建由 48% 推进至 51-52%），前次 affinity 策略有效故不再重复；
  新断点在 `src/platform/datapath_epoll.c:241/280/1840 CMSG_NXTHDR处-Werror,-Wsign-compare`，
  系 OHOS musl `sys/socket.h:360` 宏展开为 unsigned long 与 long 比较，上游 `-Werror+-Wextra`
  将其升级为错误（inotify-tools 有同类 `-Wno-sign-compare` 先例）。比较在系统头宏内、非上游逻辑，
  本轮换路线：`source()` 对顶层 `CMakeLists.txt` 的 `QUIC_WARNING_FLAGS` 追加
  `-Wno-error=sign-compare`（警告保留、其余仍为错误），不动 datapath 逻辑、不降测试口径。

- 2026-09-17 上游测试超时新失败域：全量 `ctest --output-on-failure` 在真机 2400 秒超时、
  `discovered=0/executed=0` 零汇总（msquictest 约1681 端到端用例需实时 UDP 回环 QUIC 握手与
  自签证书，沙箱内永不结束）。构建本身已过（`Configuring done`、此前 musl/签名修复有效），
  故换路线走 knowledge E344 口径：`source()`/`build()` 不动，`build()` 内测试命令收敛为
  `ctest -R "msquiccoretest|msquicplatformtest" --output-on-failure --timeout 600`
  （仅自包含单元子集；单测 `--timeout 600` 防单个挂起重演 2400 秒无裁决超时，harness 全局
  1500 秒兜底并保留部分输出）；`HMBS_UPSTREAM_TEST_RESULT` 改按 gtest 级汇总解析
  （`[==========] N tests ran` / `[  PASSED  ]` / `[  FAILED  ]` 跨两二进制求和，
  ran 未入账余量计失败不计通过），`command` 字段如实记录实际命令；MANIFEST.yml 新增
  `excluded_upstream_tests` 声明 msquictest 排除及 2400 秒超时证据，`assertion_count`
  收敛为单元子集约274（208+66文档示例值，确切数以真机为准）；test_package 陈旧缓存
  fallback 改为 `status:failed/discovered:0` 诚实缺数（重建 regenerates，不再伪造
  1955/1955）；PR 正文通过率以真机单元实测为准，补充说明声明约1681 e2e 未运行。

- 2026-09-17 round-3（与 round-2 不同策略；round-2 的 `ctest -R` 范围缩减已验证失败：
  `msquiccoretest Timeout` 零汇总 + `msquicplatformtest Failed` 的 TlsTest 初始化失败、
  50 跳过/52 通过/102 发现）。新证据链：`TlsTest::SetUpTestSuite` 首个断言即
  `CxPlatGetSelfSignedCert(...) != nullptr`（src/platform/unittest/TlsTest.cpp），而
  `src/platform/selfsign_openssl.c` 把证书目录硬编码为 `/tmp/quictest.XXXXXX`
 （`TEMP_DIR_TEMPLATE`，无视 $TMPDIR），真机 /tmp 只读致 `mkdtemp` 失败、证书返回 NULL；
  其余 52 个 platform 用例通过证明 quictls 密码学与 datapath 本身正常。新策略：
  ① `source()` 补丁 honor $TMPDIR（HMBS 任务 tmpdir）回退 /tmp，加 `#include <stdlib.h>`、
  TU 内 `#define MAX_PATH 50→512`（HMBS 路径约 100 字符，原 50 装不下），两个
  `glob+mkdtemp` 块（`FindOrCreateTempFiles`/`FindOrCreateTempCaFile`）一次性全替换，
  无测试逻辑改动；② 执行改按 gtest suite 分片直调二进制（90 秒/片、全局 1400 秒预算），
  挂起只 Attribution 到单个 suite，其余如实汇总，未启动片计 skipped+reason，
  ran 未入账余量计失败；`framework` 字段如实改为 `gtest-shards`。
  证伪：本地仿真 PASS/FAIL/KILLED/EMPTY 四场景（round-2 已验证解析语义）；
  真机以分片 verdict 日志为准定位 core 挂起点。
- 2026-09-17 round-4（与 round-3 不同策略；round-3 的 TMPDIR 补丁已验证生效：
  TlsTest 由 50 跳过变为 43 通过/1 失败，其余全部通过，证明证书生成已恢复、
  quictls 密码学与 datapath 正常）。新证据为单例失败
  `msquicplatformtest TlsTest.: listed=44 passed=43 failed=1 [rc=1]`，
  非初始化失败（否则 44 全失败），而是单个功能断言失败；现有 harness 只记
  分片计数不记失败用例名，截断摘要无法定位。本轮换路线：① 不动证书补丁与
  测试口径（不删断言、不跳过）；② `_run_upstream_tests` 新增失败名提取
  `_failed_names()`（解析 `[FAILED] Suite.Test`，过滤汇总行），失败时把
  `FAILED test:` 名与 `Failure/Which is:/Expected:/Actual:/Incorrect` 上下文
  直接写入 `shard_lines`（随 InvalidConfiguration 信息进入 HMBS 摘要，tail
  加长至 30 行），下一轮即可按名定向修复；③ 每分片进程使用独立
  `TMPDIR/shard_<bin>_<suite>` 子目录（父目录仍为 HMBS 注入可写区），消除跨
  二进制/跨分片复用 stale `quictest.*` 目录这一 flake 变量，suite 内 44 用例
  同进程共享不变。证伪：下轮预检摘要若出现 `FAILED test: TlsTest.Xxx` 即达
  诊断目标，再按该用例源码定向修；若 44/44 全过则隔离与诊断均生效。
- 2026-09-17 round-5（与 round-4 诊断隔离策略不同；round-4 的诊断已验证生效：
  摘要首次透出 `FAILED test: TlsTest.HandshakeCertFromFile` +
  `TlsTest.cpp:871 Expected: (nullptr) != (CertParamsFromFile)` +
  `Incorrect validation Status: 200000514`）。根因链：上游
  `src/platform/unittest/TlsTest.cpp` 的 `SetUpTestSuite` 仅当 `PfxPath !=
  nullptr` 才填充 `CertParamsFromFile`（`QUIC_DISABLE_PFX_TESTS` 未定义时），
  而 `HandshakeCertFromFile` 直接断言其非空；上游 `scripts/test.ps1` 经
  `install-test-certificates.ps1` 生成 `selfsignedservercert.pfx` 再由
  `run-gtest.ps1` 以 `-PfxPath:$PfxFile` 传入（`main.cpp GetValue` 解析
  `-PfxPath:xxx`），配方此前未传该参数故该用例在真机必败，其余 43 通过证明
  TLS 功能正常。新策略为低成本补齐而非跳过：`_run_upstream_tests` 前新增
  `_ensure_test_pfx()`，用真机 `openssl` 生成等价 localhost PFX（CN=localhost、
  SAN=localhost/127.0.0.1/::1、EKU=serverAuth、password=PLACEHOLDER 与上游
  `PfxPass` 一致），落盘于可写区 `hmbs-testcerts/` 并复用（24 小时内直接复用），
  各分片命令追加 `-PfxPath:<file>`（`command` 字段如实记录）；找不到 openssl
  时返回 None 并 warning，原失败如实保留、不伪造通过。证伪：下轮摘要若
  `TlsTest.: listed=44 passed=44` 即补齐生效；若仍报同名单失败则按其新上下文
  继续定向修。
- 2026-09-17 round-6（与 round-5 的 `-addext` 路线不同；round-5 补齐方向正确但
  真机证据为 `WARN: test PFX generation failed: Command [.../openssl, req,
  -x509, ...]` 非零退出，PFX 未生成故同单例复现）。根因为 sandbox 的
  harmonybrew openssl 不接受多 `-addext`（或 `IP:::1` 解析）写法。新策略仍为
  低成本补齐、换兼容路线：改用配置文件 + `-extensions v3_req -extfile`（兼容
  至 1.0.2，SAN 改写为 `IP:0:0:0:0:0:0:0:1` 避免 `::` 解析歧义），失败再退化
  为无扩展裸 `req -x509 -subj /CN=localhost`（该用例客户端关闭校验，SAN 为
  best-effort 非必需）；`pkcs12 -export` 口令仍为 `PLACEHOLDER` 对齐 `PfxPass`。
  不跳过用例、不改断言。证伪：下轮若出现 `test PFX generated` 且 `TlsTest.
  listed=44 passed=44` 即生效；若仍 WARN 则按新 stderr 定向修。
- 2026-09-17 round-7（第 2 策略周期；与前三轮动态 `openssl req -x509` 路线不同，前三轮连续未通过故停用相同假设/命令）：
  重读本轮真机证据：`test cert SAN variant failed, bare fallback ok: req: Multiple digest or unknown
  options: -sha256 and -extfile`，证明预检机 openssl 不接受 `req -x509 -sha256 -extensions -extfile`
  组合（上一方案“换兼容 flag 即可生成 SAN 证书”假设无效）；裸回退虽能产出 PFX 但丢弃 SAN/EKU，
  与 `Incorrect validation Status: 200000514` 上下文结合，存在握手校验风险，且摘要中段被省略、
  尾部 30 行全 pass 仍判失败，说明失败分片（疑似 `TlsTest.` 44 例主体）仍在省略区、裸证书未根治。
  新路线彻底不再依赖真机 `req`：以 `cryptography` 一次性生成 10 年期 localhost 证书
  （CN=localhost，SAN=DNS:localhost/127.0.0.1/::1，EKU=serverAuth，CA:FALSE，RSA2048/SHA256，
  PFX 口令 PLACEHOLDER 对齐上游 PfxPass），提交 `testcerts/`（PFX+PEM+gen_testcerts.py），
  配方新增 `exports_sources="testcerts/*"`，`_ensure_test_pfx` 主路径经 recipe/export_sources
  定位静态 PFX 并拷贝至可写 TMPDIR（零 openssl 调用）；Fallback1 仅用 `pkcs12 -export` 合成
  静态 PEM（该子命令在真机已证可用）；Fallback2 保留单条无 `-sha256/-extfile` 的 legacy `req`
  兜底。不删断言、不跳过用例。证伪：下轮若出现 `test PFX static copy` 且
  `TlsTest.: listed=44 passed=44` 即生效；否则按新透出的 `FAILED test:` 名继续定向修。
- 2026-09-17 round-8（同一指纹第 2 次修复，换策略；前次静态 PFX 路线已验证生效：日志出现 `test PFX static copy` 且 `msquicplatformtest TlsTest.: listed=44 passed=44`，HandshakeCertFromFile 单例失败已消除，故不再动证书生成）：新矛盾是全部可见分片 `failed=0 skipped=0 [rc=0]`仍被 harness 判 failed，尾部 30 行全 pass 说明失败分片在省略区（早于 TransportParamTest 的早期 core 套件）或计数汇总异常，而原 `raise ... shard_lines[-30:]` 在套件数>30 时会把真正的失败证据截掉。本轮只改失败上报、不改测试执行与口径：异常信息改为总数行 `totals: discovered/executed/passed/failed/skipped` + fatal + 全部失败行（FAILED test/ctx/TIMEOUT/ERROR/not started/failed=/skipped=/非零rc）优先列出 + 首尾各 10 行；全 pass 时的 else 分支保留首 10 行以证伪计数问题。不删断言、不跳过用例、不缩范围。证伪：下轮摘要若带 `totals:` 与 `failures (N)` 即达诊断目标，再按透出的分片名定向修。

- 2026-09-17 round-9 (第 3 策略周期；与前两轮证书/上报路线不同，前轮静态 PFX 已验证生效：`test PFX static copy` 且 `TlsTest. 44/44`，Handshake 单例已消除，故不再动证书生成）：新失败域为 `totals: discovered=467 executed=467 passed=463 failed=1 skipped=3`，其中 `SpinFrame. listed=1 passed=0 failed=1 [TIMEOUT]` 为唯一真失败，`SettingsTest. listed=17 passed=14 skipped=3 [rc=0]` 为合法跳过。重读源码：`src/core/unittest/SpinFrame.cpp` 的 `SpinFrame1000000` 做 100 万次随机帧解码（每轮 3 次 CxPlatRandom），单 job 沙箱 90 秒跑不完而非逻辑错误；`SettingsTest.cpp` 三个存储用例在 `CxPlatStorageOpen("Apps\\MsQuicUnitTestStorage")` 返回 NOT_SUPPORTED 时显式 `GTEST_SKIP`（Windows 风格路径在 Linux 不可用），rc=0 属上游预期口径。新路线：① `SpinFrame` 分片超时 90→600 秒、全局 BUDGET 1400→1800 秒，不改上游循环次数与断言；② harness  verdict 不再把 `skipped>0` 判失败（仅 `failed>0`/fatal/零测试/执行缺数判失败），失败行过滤同步移除 `skipped=` 条款，跳过数仍如实上报。证伪：下轮若 `SpinFrame. listed=1 passed=1 [rc=0]` 且总数 `failed=0 skipped=3 status=passed` 即生效；若仍 TIMEOUT 则按新透出的耗时继续定向修。

- 2026-09-17 round-10 (同一指纹第 2 次修复，换策略；前次仅放宽超时 90→600 秒/BUDGET 1400→1800 已验证无效：本轮真机仍 `SpinFrame. listed=1 failed=1 [TIMEOUT]`，且命令串已含 `SpinFrame 600s` 证明新超时已生效，故“再加超时即可跑完”假设被证伪)：重读源码，`src/core/unittest/SpinFrame.cpp` 的 `SpinFrame1000000` 每轮 3 次 `CxPlatRandom`（1B+0~255B+2B），共约 300 万次小 read；`src/platform/platform_posix.c` 的 `CxPlatRandom` 每次直调 `read(RandomFd,...)`，在单 job 沙箱中每次小 read 都陷入拦截，600 秒仍跑不完而非逻辑错误。新路线不再调超时数值，改为平台层小读合并：`source()` 新增 `CxPlatRandom` 批量补丁（每线程 4KB 缓存、一次 read 补充，大请求直通旁路；字节仍全部来自 /dev/urandom，密码学质量不变；用 `CxPlatCopyMemory`，无需新头文件），上游循环次数与断言不动。证伪：下轮若 `SpinFrame. listed=1 passed=1 [rc=0]` 即批量生效；若仍 TIMEOUT 则按新透出的分片耗时继续定向修。

- 2026-09-17 round-11 (同一指纹第 2 次修复，换策略；前次 urandom 批量补丁已验证生效：本轮真机 `discovered=467 executed=467 passed=464 failed=0 skipped=3`，SpinFrame TIMEOUT 已消除、`TlsTest. 44/44` 保持，故不再动随机数与证书路线)：新失败域仅剩 3 个 GTEST_SKIP，`HMBS_UPSTREAM_TEST_RESULT status=passed` 仍被后端判 incomplete（`上游测试未完整执行：467/467`，门禁要求 skipped=0）。重读上游源码：`src/core/unittest/SettingsTest.cpp` 的 `QuicSettingsLoad_SetsFieldsFromStorage / DoesNotOverwriteSetFields / UsesDefaultIfStorageMissing` 在 `CxPlatStorageOpen("Apps\\MsQuicUnitTestStorage",...)` 返回 NOT_SUPPORTED 时显式 `GTEST_SKIP`；而 `src/platform/storage_posix.c` 全平台 stub（`// TODO` 直接返回 NOT_SUPPORTED），Linux/OHOS 必跳，非 OHOS 特有缺失（`src/platform/unittest/StorageTest.cpp` 在 CMake 中已注释不编）。新路线为低成本补齐而非改测试口径：`source()` 用文件存储重写 `storage_posix.c`（每 storage path 落盘 `<TMPDIR>/msquic-storage-<sanitized>`、每 value 一个文件；CREATE 建目录、OPEN_EXISTING 缺目录报 NOT_FOUND；Read 缺文件报 NOT_FOUND/空 Buffer 报长度/小 Buffer 报 BUFFER_TOO_SMALL；Write/Delete/Clear 对应 fwrite/unlink/遍历清理；复用 HMBS 注入 TMPDIR 回退 /tmp，与 selfsign 补丁同源）。不删断言、不跳过用例。证伪：下轮若 `SettingsTest. listed=17 passed=17 skipped=0` 且总数 `failed=0 skipped=0 status=passed` 即补齐生效；若仍有 SKIP 则按新透出的套件名继续定向修。

- 2026-09-18 round-12（CI 基建轮，非测试失败轮；round-11 后真机已 `failed=0 skipped=0 status=passed`，但 GitCode CI 的 checkout-pr 步骤连续失败：`error: missing binary patch data for 'archives/l/libmsquic/2.5.7/testcerts/selfsignedservercert.pfx'`，兜底 `patch -p1 --fuzz=3` 又因 worker 端 busybox patch 不支持 `--fuzz` 直接报 `Unknown option`，`[ERROR] PR 10620 diff 无法应用`）：根因不在源码而在 CI 取源机制——checkout-pr 下载的 `/pull/10620.diff` 文本不含二进制文件内容，`git apply` 对新增二进制必报 missing binary patch data，属于结构性限制，重试无法自愈。新路线：把 round-7 已在真机验证过的静态 PFX（2630 字节，`TlsTest. 44/44` 的同一证书）转存为 base64 文本 `testcerts/selfsignedservercert.pfx.b64`（47 行/3555 字符，SHA256 往返校验一致）提交，删除二进制 `selfsignedservercert.pfx`；`_ensure_test_pfx` 在静态拷贝路由之后新增 stdlib `base64.b64decode`（`validate=False` 容忍换行）解码路由，字节级还原后落盘可写 TMPDIR，零外部依赖；Fallback1（PEM+`pkcs12 -export`）与 Fallback2（legacy `req`）保持不变；`gen_testcerts.py` 同步产出 `.b64`。PR 净 diff 从此不含任何二进制内容，checkout-pr 的 `git apply` 可干净应用。不删断言、不跳过用例、测试口径与统计（467/467）不变。证伪：下轮 CI 若 checkout-pr 通过并进入构建，且真机复验仍出现 `test PFX from b64 text` 且 `TlsTest.: listed=44 passed=44` 即生效；若 CI 仍报 diff 无法应用则检查是否还有其他二进制文件入库。
