# rtrlib 0.8.0 适配笔记

## 编译环境

- 构建系统：cmake（上游 `CMakeLists.txt`，`cmake_minimum_required(VERSION 2.6)`）
- 编译日期：2026-09-15
- 编译器：clang 15（HarmonyOS PC 真机，conan profile `ci/conan/profiles/ohos-aarch64`）
- 状态：built（配方已完成，待 HMBS 真机预检通过后由后端提交）
- 源码：`https://github.com/rtrlib/rtrlib/archive/refs/tags/v0.8.0.tar.gz`（262281 字节，sha256 见 conandata.yml，已本地校验解包无误）

## 编译步骤

1. `get()` 下载上游 v0.8.0 归档并解包（顶层目录 `rtrlib-0.8.0`，`strip_root=True`）。
2. `CMakeToolchain` 生成工具链：`BUILD_SHARED_LIBS=OFF`、`RTRLIB_TRANSPORT_SSH=OFF`，OHOS 下 `CMAKE_SYSTEM_NAME=Linux`。
3. `cmake.configure()` + `cmake.build()`：构建 `rtr` 共享库、`rtrlib_static` 静态库（上游测试链接用）、`rtrclient` / `rpki-rov` 工具。
4. `ctest -E "live_validation|dynamic_groups" --output-on-failure`：运行上游 6 项离线测试（2 项需联网的在线用例按执行层面排除），6/6 全过；声明 discovered=9（上游 tests/ 顶层共 9 个测试源码文件，避免少报）。
5. `cmake.install()`：安装库、公开头文件（`include/rtrlib/`）、pkg-config 文件、工具与 man 页。
6. `test_package`：以消费者视角 `find_package(rtrlib)` 链接已安装库，运行 2 项真实 API 测试。

## 上游测试盘点（源码审计）

上游 `tests/` 目录顶层共 9 个测试源码文件（discovered=9），其中 8 项经 `ADD_TEST` 注册，1 项（test_pfx_locks）仅构建未注册：

| # | 测试 | 说明 | 离线可运行 |
|---|------|------|-----------|
| 1 | test_pfx | pfx 表（含约 19 万条记录批量用例） | 是 |
| 2 | test_trie | trie 前缀树 | 是 |
| 3 | test_ht_spkitable | SPKI 哈希表 | 是 |
| 4 | test_ht_spkitable_locks | SPKI 并发锁 | 是 |
| 5 | test_live_validation | 在线校验，需访问公网 RPKI 缓存 | 否（排除） |
| 6 | test_ipaddr | IP 解析转换 | 是 |
| 7 | test_getbits | 位操作工具 | 是 |
| 8 | test_dynamic_groups | RTR 管理器动态分组（同样硬编码连接公网缓存并等待同步，离线用 -E 排除） | 否（排除） |
| 9 | test_pfx_locks | pfx 表并发锁；上游 CMakeLists 仅构建、`ADD_TEST` 已注释未注册 | 否（上游未注册，无从运行） |

此外 `tests/unittests/` 下 2 项 cmocka 单测需 `UNIT_TESTING=ON`（上游默认关闭，需 cmocka 依赖，本次未启用），不计入 discovered。

离线真机实际执行 6 项（discovered=9 − skip 3：在线 2 项 + 未注册 1 项），子集 6/6 全过，声明 skipped=3 并在 HMBS 标记 reason 中如实说明。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | test_live_validation 在离线环境必然失败 | 用例硬编码连接公网缓存 rpki-validator.realmv6.org:8283，无此外网依赖 | 构建中 `ctest -E "live_validation|dynamic_groups"` 排除（本轮确认 dynamic_groups 同属在线用例，见第 9 条），MANIFEST.yml 与 PR 补充说明如实声明 |
| 2 | 是否引入 libssh/cmocka 依赖 | 两者在制品仓状态均为 built（未 published），按 R36 不得引入 | 默认零依赖；SSH 与 cmocka 单测均关闭，记录为已知限制 |
| 3 | 上游同时构建共享与静态两个目标 | 上游 `install(TARGETS rtrlib)` 仅安装共享库，静态目标只供测试链接 | 保持上游行为，`package_info` 声明 `libs=["rtr"]` |
| 4 | `cmake_minimum_required(VERSION 2.6)` 较旧 | 上游写法，CMake 3.x 仅报 deprecation 警告仍可配置 | 首轮不打补丁；若真机 CMake（4.x）拒绝配置，再升级该声明并走补丁流程 |
| 5 | 真机预检 configure 失败：`The C compiler identification is unknown`（clang）+ `can't create temporary file /tmp/...` | 第一轮 policy/TMPDIR/-pipe 修复后复检仍同指纹失败（报错行 52→75 证明新代码已运行；Compatibility 报错消失，残留纯编译器 try-compile 失败）。crunch-dxtc/0.56.2 同指纹三轮同败，根因为工具链携带沙箱缺失的 profile 编译器绝对路径 | 第二轮换路线：`_find_compiler()` 存在性校验与回退 + 工具链陈旧路径替换 + SYSTEM_NAME 改 cache 注入 + TMPDIR 能力优先级候选（已验证生效，见第 6 条日志证据） |
| 6 | 真机 configure 通过、Generate 步失败：`RT_LIB ... set to NOTFOUND, linked by target "rtrlib"`（第二轮编译器 fallback 已生效：日志见 `CMAKE_C_COMPILER=.harmonybrew/bin/clang` 且 Threads 检出通过） | 新失败域：上游 `find_library(RT_LIB rt)` 在 OHOS/musl 上必然 NOTFOUND（无独立 librt，clock_gettime 等并入 libc），但 `set(RTRLIB_LINK ${RT_LIB} ...)` + `target_link_libraries` 无条件引用，Generate 步硬报错 | 本轮换路线（与前两轮不同，不动编译器逻辑）：`generate()` 中 OHOS 下预置 `tc.cache_variables["RT_LIB"]=""`，使 find_library 命中缓存跳过搜索，链接表自动 drop 空值（ettercap/0.8.4.1 LIB_RT 同理；因 RT_LIB 直接进链接表故置空而非指 libc）。若仍报 NOTFOUND，下轮改上游 CMakeLists 补丁守卫。待 HMBS 下一轮真机预检验证 |
| 7 | 真机 link 失败：`ld.lld: undefined reference due to --no-allow-shlib-undefined: pthread_setcancelstate / pthread_cancel referenced by librtr.so`（RT_LIB 置空后 Generate/compile 已通过，librtr.so 本体编出，仅 tools/rtrclient 链接报错） | 新失败域：OHOS musl 未实现 POSIX 线程取消 API（E085/E127；s3fs-fuse/sysbench 同类）。上游 rtr.c/packets.c/tcp_transport.c 直接调用 pthread_cancel/setcancelstate，headers 有声明故编译通过，但 libc 无实现，--no-allow-shlib-undefined 把 .so 的未定义符号升级为可执行文件链接错误 | 本轮换路线（不动 RT_LIB/编译器逻辑）：新增 `patches/0001-ohos-pthread-cancel-stub.patch`，往 RTRLIB_SRC 追加 `rtrlib/lib/ohos_pthread_compat.c`（OHOS 下提供 4 个 no-op stub，非 OHOS 编为空 TU 不覆盖 glibc 真实现；OHOS 激活经 `RTRLIB_OHOS_PTHREAD_STUB` 预定义 + `__OHOS__` 双守卫），`package_info` 补 `system_libs=["pthread"]`。离线单测不走 cancel 路径，语义不受影响。待 HMBS 下一轮真机预检验证 |
| 8 | 真机 build 步失败：`ConanException: Failed to parse patch: .../0001-ohos-pthread-cancel-stub.patch` + `WARN: extra lines for hunk no.1 at 14`（compile 阶段，export/patch 之后即停；/tmp 只读报错来自 preflight.sh 自身 mktemp，非配方阻塞） | 新失败域：补丁文件 hunk 头行数与实际不符。hunk1 声明 `+39,10`，实际旧 6 行 + 新增 5 行 = 新 11 行；hunk2（新文件）声明 `+1,26`，实际 36 行。conan 的 Python patch 解析器按声明计数严格切分，多余 1 行即判 parse 失败 | 本轮只修补丁头（不动配方/测试口径）：hunk1 改为 `@@ -50,6 +50,11 @@`（行号按上游 CMakeLists 实际位置 50 校准：`ht-spkitable.c` 行起 6 行上下文），hunk2 改为 `@@ -0,0 +1,36 @@`；LF/UTF-8 无 BOM 保持。已用 `git apply --check -p1` 与实际 apply 验证通过（新文件落点与 RTRLIB_SRC 追加均生效）。待 HMBS 下一轮真机预检验证 |
| 9 | 真机 build 步失败：上游 7 项中 `test_dynamic_groups … ***Failed 1.02 sec`（其余 6 项 Passed；开头的 `/tmp/... Read-only file system` 来自 preflight.sh 自身 mktemp，非配方阻塞；诊断 `readonly_tmp` 仅覆盖该启动噪声，配方侧 `_ensure_writable_tmp` 已生效） | 新失败域：审计 `tests/test_dynamic_groups.c` 确认其与 `test_live_validation` 同属在线用例——硬编码 `tcp_host=rpki-validator.realmv6.org:8283`，`rtr_mgr_start` 后轮询 `rtr_mgr_conf_in_sync`，离线真机 DNS/连接失败经 `connection_status==RTR_MGR_ERROR` 快速 `EXIT_FAILURE`（故仅 1.02s，而非 20s 超时）。首轮把 dynamic_groups 误判为离线用例，仅排除了 live_validation | 本轮只改测试口径（不动编译器/RT_LIB/stub 逻辑）：`build()` 改为 `ctest -E "live_validation\|dynamic_groups"`，`MANIFEST.yml:upstream_test_command` 同步，`notes.md` 盘点表第 8 行改为"否（排除）"。不断言、不改上游源码；联网缺失不可低成本补齐（需公网 RPKI 缓存），按规范在补充说明如实声明"上游 8 个用例中 2 个未运行"。待 HMBS 下一轮真机预检验证（预期 6/6 通过） |
| 10 | 真机 test_package configure 失败：`System is unknown to cmake, create Platform/HarmonyOS` + `CMAKE_C_COMPILER: /data/service/hnp/bin/clang` 报错（主库已 100% Built、上游 6 项 Passed，失败点推进到 test_package；开头的 /tmp 只读报错来自 preflight.sh 自身 mktemp，非配方阻塞） | 新失败域：test_package/conanfile.py 沿用裸 `generators = CMakeDeps, CMakeToolchain`，未同步主配方的平台/编译器修复。profile 默认把 OHOS 映射为 CMAKE_SYSTEM_NAME=HarmonyOS（vanilla cmake 无此平台文件，try-compile 必败），且 profile 编译器绝对路径在预检沙箱中不存在（主配方已回退到 .harmonybrew/bin/clang，test_package 仍用陈旧路径）。另 HMBS 证据门禁要求两行 JSON 标记，配方此前均未输出 | 本轮只修 test_package 工具链与证据（不动主库编译器/RT_LIB/stub/测试口径）：test_package 改显式 generate()，OHOS 下置 CMAKE_SYSTEM_NAME=Linux/PROCESSOR=aarch64，复用主配方 _find_compiler 存在性回退与工具链陈旧路径替换、TMPDIR 能力优先级（cmocka/tinyply 先例）；build() 与 test() 中主包与 test_package 分别经 print+output.info 双通道输出 HMBS_UPSTREAM_TEST_RESULT（6/6）与 HMBS_TEST_PACKAGE_RESULT（2/2），数字来自本轮预检已通过的 ctest 输出与 MANIFEST 审计（8-2=6，消费者 2 项），ctest 失败时 self.run/cmake.test 抛错故标记仅在通过后可达。待 HMBS 下一轮真机预检验证 |
| 11 | 真机 test_package generate 失败：`CMakeDeps is declared in the generators attribute, but was instantiated in the generate() method too`（主包已 Built、上游标记 6/6 已输出，失败点仅剩 test_package generate 第 90 行） | 新失败域：上轮新增的显式 generate() 内又写 `CMakeDeps(self).generate()`，与类属性 `generators = CMakeDeps` 重复声明，Conan 直接抛错；与上轮平台映射问题不同域 | 本轮换路线（不动平台映射/编译器回退/证据逻辑）：删 generate() 内两行 CMakeDeps 实例化，保留属性声明 + 手动 CMakeToolchain（tinyply 在仓先例同构），并删未使用的 CMakeDeps 导入。待 HMBS 下一轮真机预检验证 |
| 12 | AI Review 重复误报 validate/str_cmp 签名（同一指纹第 3 次；前两轮纯证伪未收敛） | 两 bot 引用的均非 v0.8.0 签名（分别称 4 参返回 enum、3 参返回 0），且其中一条自认 test_pfx_validation.c 无问题自相矛盾；v0.8.0 pfx.h/ip.h/ip.c 与上游 test_ipaddr.c 均证实工作树写法正确 | 本轮换策略（不动测试口径：CHECK 数仍 19+11=30，MANIFEST 不变）：两测试源各加 _Static_assert 编译期契约守卫（零运行时影响），把“签名正确”变成真机编译即证明的机械事实。待 HMBS 下一轮真机预检验证 |
| 13 | AI 指出 stub 中 `int pthread_testcancel(void)` 与 POSIX `void` 声明冲突（P2，有效） | 核对 POSIX/musl/glibc 均声明 `void pthread_testcancel(void)`，其余三 stub 的 int 返回与 POSIX 一致；真机虽通过（OHOS 头文件疑未声明该符号），int 写法仍不合规且在头文件补声明即爆 conflicting types | 本轮只改补丁一行（同行数替换，hunk 头 `+1,36` 保持有效）：`int pthread_testcancel(void){return 0;}`→`void pthread_testcancel(void){}`；5 参 P1 指控维持上轮 tarball 证伪结论不变。待 HMBS 下一轮真机预检验证 |

## 依赖版本

无外部依赖（默认选项）。可选：libssh/0.11.4（`with_ssh=True` 时，需先发布）。

## 验证结果

```bash
# 待 HMBS 真机预检（conan create 全流程：构建 + 上游 6 项 ctest + test_package 2 项 ctest）
# 本轮只交付未提交工作树，不在本机运行 conan
```

## 注意事项

- `rtrlib_static` 目标名含 `_static` 后缀，其产物不安装，仅供上游测试链接。
- 包内 `bin/rtrclient`、`bin/rpki-rov` 为上游默认工具；配方 `package_type` 为 library，按 L0k/PF8 口径不创建 commands.json。
- 本配方未验证通过前，`manifest.yaml` 状态保持 built，不标 published。
- R40 stub 人工确认（0001 补丁）：4 个 no-op stub 仅解决 OHOS/musl 缺 pthread_cancel 族导致的 `--no-allow-shlib-undefined` 链接未定义符号；离线 pfx 校验与上游 6 项离线测试均不经过 cancel/join 路径，真机 6/6 通过即覆盖；TCP 在线会话的 cancel 语义在 OHOS 上为 no-op，属已知限制已在 PR 补充说明声明。
