# libtins 4.5 适配笔记

## 构建配置

- 分支：`feat/libtins-4.5`
- 任务号：13521（开源鸿蒙PC专项积分赛-依赖，activity_id=6）
- 构建系统：CMake（上游 `CMAKE_MINIMUM_REQUIRED(VERSION 2.8.1)`，库使用 C++11 特性）
- 包类型：library（默认静态；`shared` 选项可切动态）
- 依赖：
  - `libpcap/1.10.6`（抓包与离线 BPF 过滤，`LIBTINS_ENABLE_PCAP`）
  - `openssl/3.5.6`（WPA2 解密，`LIBTINS_ENABLE_WPA2`）
  - `boost/1.84.0`（仅表头：`boost.icl` 供 ACK tracker、`boost.any` 供 TCP stream custom data）
  - `gtest/1.17.0`（test_requires，上游 tests/src 的 GoogleTest 套件）
- 源码：`https://github.com/mfontanini/libtins/archive/refs/tags/v4.5.tar.gz`
  sha256 `6ff5fe1ada10daef8538743dccb9c9b3e19d05d028ffdc24838e62ff3fc55841`
  （与 `codeload.github.com/mfontanini/libtins/tar.gz/refs/tags/v4.5` 实测同一 tarball）

## OHOS 适配要点

1. **CMAKE_SYSTEM_NAME=Linux（E092）**：CMake 无 HarmonyOS 平台模块。上游顶层
   CMakeLists.txt 用 `IF(UNIX)` 决定 pkg-config 安装、`lib/cmake/libtins` 配置目录
   与库名约定；不设 Linux 时这些分支走到默认值，产物布局与上游不一致。generate()
   中强制 `CMAKE_SYSTEM_NAME=Linux`，与上游 Linux 行为对齐。

2. **上游 googletest submodule 缺失 → 走 `find_package(GTest)` 分支**：GitHub
   release tarball 不含 `googletest/` 子模块内容（目录为空），上游
   `IF(EXISTS .../googletest/CMakeLists.txt)` 不成立，落到 `ELSE()` 的
   `FIND_PACKAGE(GTest QUIET)`。该分支只做 `ENABLE_TESTING()` +
   `ADD_SUBDIRECTORY(tests)`，**没有设置** `GOOGLETEST_INCLUDE` /
   `GOOGLETEST_LIBRARY`（这两者在子模块分支才有值），而
   `tests/src/CMakeLists.txt` 直接用这两个变量做 `INCLUDE_DIRECTORIES` /
   `LINK_DIRECTORIES`。配方在 generate() 里从 Conan 的 `gtest` 包
   （`self.dependencies` 的 `cpp_info.includedirs/libdirs`）取绝对路径写入这两个
   cache 变量，使 `LINK_LIBRARIES(gtest gtest_main ...)` 能被解析。未修改上游
   任何文件，无需补丁。

3. **上游测试二进制是 EXCLUDE_FROM_ALL**：`tests/src/CMakeLists.txt` 用
   `CREATE_TEST` 宏逐个 `ADD_EXECUTABLE(... EXCLUDE_FROM_ALL)` 并挂到聚合目标
   `tests`。因此 build() 在 `cmake.build()` 之后必须再
   `cmake.build(target="tests")`，否则一个测试二进制都不会生成（历史教训：只跑
   `cmake.build()` 会得到"0 个测试可执行"）。

4. **OHOS 上运行交叉构建的测试二进制：ELF 自签 + CONFIG_SHELL bash**：测试可执行
   在设备上执行前逐个 `binary-sign-tool sign -selfSign 1` 签名（签名后校验
   `.codesign` 段数量为 1），并用 `CONFIG_SHELL`（hnp bash）而不是
   `/system/bin/sh` 启动 ctest（mksh 无法加载动态链接二进制）。

5. **测试运行期库路径**：ctest 通过 `source <generators>/conanrun.sh` 引入 Conan
   依赖的 `LD_LIBRARY_PATH`（libpcap/openssl/boost 若为动态包），并追加构建树
   `lib/` 目录，覆盖被测共享库场景。

6. **特性选项与上游一一对应**：`with_pcap`/`with_dot11`/`with_wpa2`/
   `with_ack_tracker`/`with_tcp_stream_custom_data` 直接映射上游同名 CACHE
   选项；关掉某特性只让该特性编译期消失，不改变已注册的 ctest 项集合（除按上游
   逻辑本就随特性开关增减的项）。`boost` 只在 `with_ack_tracker` 或
   `with_tcp_stream_custom_data` 打开时成为依赖。`examples` 关闭（`LIBTINS_BUILD_EXAMPLES=OFF`），
   上游 examples 只是示例程序、不参与测试。

## 上游测试接入

- `tests/src/CMakeLists.txt` 的 `CREATE_TEST` 宏逐项 `ADD_TEST`，ctest 注册项：
  - 基础 37 项（address_range … vxlan）
  - `LIBTINS_ENABLE_PCAP=ON`：+2（offline_packet_filter、tcp_stream），并再开 DOT11 时 +1（ppi）
  - `LIBTINS_ENABLE_DOT11=ON`：+20（dot11/ack … dot11/rts、radiotap、wep_decrypt）
  - `LIBTINS_ENABLE_WPA2=ON`：+1（wpa2_decrypt）
  - 合计 **61 个 ctest 条目**（本配方默认全开）
- gtest 原子用例：`tests/src/**/*_test.cpp` 中 `TEST(` 35 个 + `TEST_F(` 776 个
  = **811 个原子用例**，由上述 61 个可执行文件承载。
- build() 末尾执行 `ctest --output-on-failure -V -j1`，解析 gtest
  `[  PASSED  ] N tests` / `[  FAILED  ] M tests` 汇总行，输出
  `HMBS_UPSTREAM_TEST_RESULT` 标记；退出码非 0 或失败数 >0 时 raise 并把日志尾部
  写入错误输出。

## 验证

- 真机 W3（conan create，OHOS aarch64 profile，`libtins/4.5@ohpcd/stable`）：
  - 上游测试（`ctest --output-on-failure -V -j1`，61 个可执行文件）：
    **809/809 通过，0 失败，0 跳过**
    （`HMBS_UPSTREAM_TEST_RESULT={"status": "passed", "discovered": 809,
    "executed": 809, "passed": 809, "failed": 0, "binaries": 61}`）
  - 静态口径核对：`tests/src/**/*_test.cpp` 共 811 个 gtest 注册宏
    （`TEST(` 35 + `TEST_F(` 776），其中 2 个在本构建中不参与：
    ① `tests/src/pktap_test.cpp` 的 1 个用例——上游 `tests/src/CMakeLists.txt`
    没有为它注册 ctest 目标（BSD/macOS 专用文件），从不编译；
    ② `tests/src/tcp_ip_test.cpp` 的 `TEST(Foo, Dummy)`——位于
    `#ifdef TINS_HAVE_TCPIP` 的 `#else` 分支，启用 TCP/IP 支持（本配方默认）
    时被排除。故编译基数 = 执行数 = **809**。
  - 消费者测试（test_package，`test_libtins`）：**17/17 断言通过**
    （`HMBS_TEST_PACKAGE_RESULT={"executed": true, "passed": true,
    "discovered": 17, "passedCount": 17}`，与 `test_package/MANIFEST.yml` 的
    `assertion_count: 17` 同源）
- 适配后合计 = 809（上游执行）+ 17（消费者）= **826 ≥ 811（上游静态）**。

## 下一步

- W4 审计 → `submit` → CI/AI → 提审。

## 路径判定（AGENTS §6.2）

结论：**路径 A（基础适配）**，不申报路径 B。理由：本次适配的每个手法都是仓内既有知识/惯例的应用，
未形成可跨仓库复用的**新增**知识——

- E092（CMake 无 HarmonyOS 平台模块 → 强制 `CMAKE_SYSTEM_NAME=Linux`）：知识库已有该条目；
- CMake 4 的 `CMAKE_POLICY_VERSION_MINIMUM=3.5`：仓内 292 个配方的同类修法；
- 把 Conan 的 gtest 包注入上游 `GOOGLETEST_INCLUDE`/`GOOGLETEST_LIBRARY` 变量：属 E092 与上游
  `find_package(GTest)` 分支的具体应用；
- 静态 libtins 需为上游测试补链 OpenSSL：常规链接知识；
- 宿主签名工具需剔除构建环境注入的 `LD_LIBRARY_PATH`：知识库 E452/E077/E083/E318 已覆盖
  OHOS ELF 签名链路，本次只是环境净化的实现细节，未构成独立新条目。

查重范围：`knowledge/doc/`、`knowledge/graph/index.tsv`、`knowledge/drafts/`，未发现本次可新增的独立主题。
---

**编译结束**: 2026-09-16 12:27
**最终状态**: built
