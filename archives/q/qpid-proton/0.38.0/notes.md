# qpid-proton 0.38.0 适配笔记（HarmonyOS PC / aarch64）

## 编译环境
- 构建系统: cmake（上游 `cmake_minimum_required(VERSION 2.8.12)`）
- 编译日期: 2026-09-21
- 编译器: clang/clang++ 15.0.4（`/data/service/hnp/bin/clang`，target aarch64-unknown-linux-ohos）
- conan: 2.29.1（OHOS 适配版）+ profile `ci/conan/profiles/ohos-aarch64`
- 命令: `conan create archives/q/qpid-proton/0.38.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing` → `rc=0`

## 上游信息
- 上游仓库: https://github.com/apache/qpid-proton （Apache Qpid Proton，AMQP 1.0 消息库）
- 源码包: https://github.com/apache/qpid-proton/archive/refs/tags/0.38.0.tar.gz
- sha256: `b18ed91d15d8d12cbc9fce4de55f102f23a71c9c266e9d04b66e8c516b978d59`（1490563 字节；双源核对：本仓下载实测 + openmama 预研留存的同名 tar）
- 许可证: Apache-2.0
- 产物: `libqpid-proton.so`（legacy：messenger+reactor+core+proactor 全量）、`libqpid-proton-core.so`、`libqpid-proton-proactor.so`；
  头文件 `include/proton/*.h`（含 `version.h`）；CMake 包配置 `lib/cmake/Proton/ProtonConfig.cmake`（`find_package(Proton)`）；
  pkg-config `lib/libqpid-proton{,-core,-proactor}.pc`；`share/proton/**`（上游测试/示例/互操作数据，上游安装规则原样保留）
- 不安装可执行文件（`c/tools/*` 只构建不安装），因此包内无 `bin/`（R38 commands.json 不适用）

## 编译步骤（配方实际传入的开关）

```python
tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"          # E092：CMake 无 Platform/HarmonyOS
tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
tc.variables["LIB_SUFFIX"] = ""                      # 否则 Linux 分支装到 lib64/
tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
tc.variables["BUILD_TESTING"] = "ON"                 # 上游 ctest 套件
tc.variables["BUILD_EXAMPLES"] = "ON"                # tests/examples 的 c-broker 目标
tc.variables["BUILD_CPP"] = "OFF"
tc.variables["BUILD_GO"] = "OFF"
tc.variables["BUILD_STATIC_LIBS"] = "OFF"
tc.variables["BUILD_TLS"] = "OFF"                    # 独立的 raw-connection TLS 库，非 messenger/reactor 路径
tc.variables["ENABLE_FUZZ_TESTING"] = "ON"           # 上游默认；语料回归测试
tc.variables["ENABLE_WARNING_ERROR"] = "OFF"
tc.variables["SASL_IMPL"] = "none"
tc.variables["SSL_IMPL"] = "openssl"                 # 依赖 openssl/3.5.8.1（静态，R26）
cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 直接构建共享库时 `readelf -d` 无 DT_SONAME，`DT_NEEDED` 记录 `c/libqpid-proton-core.so` 相对构建路径 | CMake 4.1 无 `Platform/HarmonyOS.cmake`，平台文件根本没被加载：`UNIX` 未定义、`CMAKE_SHARED_LIBRARY_SONAME_C_FLAG` 为空 | `CMAKE_SYSTEM_NAME=Linux`（仓内 288 处先例，E092） |
| 2 | 指定 Linux 后产物装到 `lib64/` | Linux 分支 `FIND_LIBRARY_USE_LIB64_PATHS=TRUE` 且指针 8 字节 → `LIB_SUFFIX=64` | `LIB_SUFFIX` 置空 |
| 3 | `ProtonTargets-release.cmake` 导出 `IMPORTED_NO_SONAME TRUE`（CI L5c 门禁失败） | 无 SONAME 的库被 CMake 标记为"无 soname 可寻址" | 见 1；`CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE` 保留不带动版本的 DT_SONAME（`libqpid-proton.so`），同时不生成 `.so.N` 软链（HMDFS 下软链别名链不可靠） |
| 4 | 配置阶段 `CMake Error: Compatibility with CMake < 3.5 has been removed` | 上游 `cmake_minimum_required(VERSION 2.8.12)` | 配置命令行传 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（cache 变量对 `cmake_minimum_required` 检查太晚） |
| 5 | `-Werror` + `-Wstrict-prototypes` 使 14 处旧式 `f()` 定义编译失败（如 `c/src/platform/platform.c:35 int pn_i_getpid()`） | 上游默认 `ENABLE_WARNING_ERROR=ON`，代码是 gnu99 时代写法，clang 15 判为 error | `ENABLE_WARNING_ERROR=OFF`（上游对 Darwin 同样关闭；不修改上游源码） |
| 6 | `BUILD_TESTING=ON` + `BUILD_EXAMPLES=OFF` 时生成阶段报 `No target "c-broker"` | `c/tests/CMakeLists.txt` 的 `c-fdlimit-tests` 与 `tests/examples` 的 `c-example-tests` 都引用 `$<TARGET_FILE_DIR:c-broker>`，该目标由 `tests/examples` 提供 | `BUILD_EXAMPLES=ON`（示例程序不安装，不入包） |
| 7 | `c-proactor-test` 首个用例挂死（ctest 1500s 超时） | **HarmonyOS 的 epoll 不实现 EPOLLONESHOT**：proactor 的 ready-list eventfd 被设计成"永久可读 + ONESHOT 触发一次"，失效后每次 `epoll_wait` 都返回它，`poller_do_epoll()` 永远拿不到"无新事件"的返回路径，`pn_proactor_get()/wait()` 自旋不返回 | `patches/0001-ohos-emulate-epolloneshot-in-epoll-proactor.patch`：投递到该 fd 后立即 `EPOLL_CTL_MOD` 置 0 事件实现 one-shot 语义（复臂路径本来就调 `rearm_polling()`）。修复后 1.9s 跑完 14/15 用例 |
| 8 | 安装后的 `libqpid-proton-proactor.so` `dlopen` 报 `Permission denied`，作为 `DT_NEEDED` 也加载失败（`Error loading shared library ...`） | OHOS 在加载时校验 ELF `.codesign` 段；CMake install 会重写"有树内依赖的库"的 RPATH（proactor 依赖 core）并抹掉构建期 RUNPATH → 字节变更 → 签名失效 | `package()` 末尾用 `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1` 重签全部 `lib/**.so`（与 openmama 配方同款），并删除测试运行产生的 `__pycache__` |
| 9 | 上游 SSL 相关 ctest 条目失败（`error:0A000415 ssl/tls alert certificate expired`） | 上游仓库内置测试证书 `c/tests/ssl-certs/{tserver,tclient}-certificate.pem` **已于 2025-11-24 过期**（notAfter=Nov 24 18:10:39 2025 GMT），任何 2025-11-24 之后跑该套件的主机（含 Linux）都会失败 | 不修改上游测试数据；配方在构建日志中输出证书 notAfter 与失败条目作为证据（见 reports/upstream-tests.md），按"上游夹具过期"归因 |

## 上游测试清点（实测，`ctest -V --timeout 120`）

- ctest 注册 **11** 条目，**9 通过 / 2 失败**：
  | 条目 | 结果 | 说明 |
  |------|------|------|
  | c-core-test | ✅ 1.5s | Catch2：72 用例 / 1299 断言 |
  | c-extra-test | ✅ 1.4s | Catch2：1 用例 / 254 断言 |
  | c-proactor-test | ❌ | Catch2：15 用例中 14 通过；唯一失败用例 `proactor_ssl`（8 断言）→ 证书过期 |
  | c-raw-connection-test | ✅ 1.4s | Catch2：2 用例 / 846 断言 |
  | c-ssl-proactor-test | ❌ | Catch2：1 用例（39 断言中 35 通过）→ 证书过期 |
  | c-fdlimit-tests | ✅ 4.0s | Python `c/tests/fdlimit.py` 驱动的 fd 上限回归 |
  | c-example-tests | ✅ 5.7s | Python `tests/examples/testme`：起真实 c-broker，7 个子用例全过（SSL 开关打开后才全过） |
  | fuzz-connection-driver / fuzz-message-decode / fuzz-url / fuzz-sniff-header | ✅ ×4 | libFuzzer `StandaloneFuzzTargetMain` 语料回归 |
- Catch2 口径合计：**91** 用例（89 通过）、**2672** 断言（2660 通过）。
- 机器证据：`build()` 打印 `QPID_PROTON_UPSTREAM_TEST_RESULT={...}` 与 `QPID_PROTON_SSL_TEST_CERT={...}`，
  完整 ctest 日志留在构建目录 `upstream-ctest.log`。

## 依赖版本
- `openssl/3.5.8.1`（制品仓已发布；静态库，链接进 `libqpid-proton.so`，无额外运行期依赖；`DT_NEEDED` 只有 `libc.so`）
- 未启用的上游可选组件：`SASL_IMPL=none`（cyrus-sasl 为上游可选，测试套件不依赖）、libuv（epoll proactor 是 Linux 默认路径，上游按 epoll→iocp→libuv 顺序取第一个可用者）、jsoncpp（仅 C++ 绑定使用，`BUILD_CPP=OFF`）

## 验证结果
- `conan create ... --build=missing` → `rc=0`；L0 静态门禁自查通过（无 patches 格式/shell 变量/硬编码 remote/未发布依赖问题）
- 包内三个 `.so` 均有 DT_SONAME、`DT_NEEDED` 无路径、`lib/cmake/**` 无 `IMPORTED_NO_SONAME`、重签后可正常加载
- test_package：`test_qpid_proton` 13/13 通过（6 项 platform：LP64、小端、musl 行为、proactor interrupt/timeout/idle 事件（patches/0001 回归）；7 项 consumer：版本宏、AMQP 1.0 线上字节一致性、消息编解码往返、pn_data map 编解码、TLS 可用、messenger 生命周期/订阅）

## 注意事项
- 包内 `libqpid-proton.so` 已静态链接 OpenSSL，`pn_ssl_present()` 为真，TLS 可用（上游 SSL 用例接通即依赖此）
- 下游 openmama 的 `cmake/FindProton.cmake` 走 module 模式，按 `PROTON_ROOT/{include,lib,lib64}` 查找：`include/proton/version.h` 与 `lib/libqpid-proton.so` 均在标准位置，设 `PROTON_ROOT=<qpid-proton 包目录>` 即可命中
- 未安装 `c/tools/{msgr,reactor}-{send,recv}`（上游无 install 规则），如需 CLI 需另加安装规则与 commands.json
