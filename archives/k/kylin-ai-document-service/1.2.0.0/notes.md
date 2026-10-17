# kylin-ai-document-service 1.2.0.0 适配笔记

## 编译环境

- OS：HarmonyOS (OHOS) 6.0，aarch64（worker 即目标平台，**原生构建**，非交叉）
- 编译器：clang 15.0.4（`/data/service/hnp/bin/clang`），libc++，C++17
- 构建系统：CMake 4.1.2 + Unix Makefiles
- Conan：2.29.1（OHOS 适配版），profile `ohos-aarch64`
- 命令：
  `conan create . --user=ohpcd --channel=stable -pr:h=$HOME/.conan2/profiles/ohos-aarch64 -pr:b=$HOME/.conan2/profiles/ohos-aarch64 --build=missing`

## 源码获取

- 官方源：`https://gitee.com/openkylin/kylin-ai-document-service`（openKylin 官方组织托管）
- tag：`build/1.2.0.0-ok0.6`（annotated tag 对象 `4cc2dcfc1e5a39544e2258348432e5c839462e6e`）
- commit：`ef12f7fae2cbc6a2f5d3c3626c96f35b5935a832`
- 归档 URL：`…/repository/archive/build%2F1.2.0.0-ok0.6.tar.gz`
- sha256：`73f416627c58a2f62d13c5e460d84c29c979d2b54ac0ffb1de4cf6669120f481`
  （两次独立下载哈希一致；解包内容与 `git clone --branch build/1.2.0.0-ok0.6 --depth 1`
  逐文件一致，已 diff 验证）
- 注意：Gitee 归档端点按 User-Agent 过滤，`source()` 显式传 `User-Agent: curl/8.0`

## 上游结构

```
CMakeLists.txt              # 顶层：共享库 + install 规则 + ENABLE_TEST 选项
document.proto              # 协议定义（service DocumentService）
include/                    # client.h / stub_manager.h / *_stub.h（公开头）
src/client.cpp              # DocumentChunkClient 实现（sd-bus + gRPC + protobuf JSON）
src/stub_manager.cpp        # 同步/异步 Stub 管理
pkg-configs/*.pc            # pkg-config 模板
python/                     # 服务端负载（分块器/解析器/data），约 3.7 MB
configs/lib/systemd/user/   # systemd user unit
test/test.cpp               # 上游唯一测试程序（ENABLE_TEST=ON 时构建）
debian/                     # deb 打包元数据（不参与 conan 构建）
```

产物：共享库（`VERSION 2.0.0` / `SOVERSION 2`）+ 公开头 + `.pc` + python 数据
+ systemd unit。**无 `bin/` 可执行产物 → 库类型，不需要 `commands.json`（R38）。**

## 上游测试申报表（R51 三步法）

### 第 1 步：清点（证据）

```
1. find . -iname '*test*' -not -path './.git/*'
   -> ./test、./test/CMakeLists.txt、./test/test.cpp；./python/pdftest.pdf（数据文件）
2. ls tests            -> No such file or directory（无 tests/ 目录）
3. grep -rn 'enable_testing|add_test|ctest' --include=CMakeLists.txt .
   -> 无结果（上游未注册 CTest）
4. test/CMakeLists.txt: target_link_libraries(test PRIVATE kylin-ai-document-service)
   -> 唯一测试程序，链接被测库
```

**结论：上游测试总数 N = 1**，无单元测试框架、无 CTest 注册。

### 第 2 步：实际运行

`conanfile.py` 的 `generate()` 设 `ENABLE_TEST=ON`（上游该选项被
`unset(... CACHE)` 中和导致命令行无法开启，补丁 0001 已调整顺序），`build()`
末尾编译并执行该程序：

```
[100%] Built target test
RUN: <build>/test/test      # 实际执行，退出码 0
```

**N′ = 1**（实际运行 1/1）。

### 第 3 步：如实回填（局限，不豁免）

| 项 | 实测 |
|----|------|
| 通过率 | 1/1（程序执行完成，退出码 0） |
| 断言 | **无**：`main()` 中 `catch(...)` 后恒 `return 0`，退出码不反映真实结果 |
| 输入 | 硬编码 `/home/kylin/文档/操作系统大会演示素材v0.2/…/公司报销制度及流程.docx`，本环境不存在 |
| 运行环境 | 依赖运行中的文档服务（unix socket）与用户 D-Bus/systemd；日志实测 `Failed to connect to user bus` + `errorCode=14 … No such file or directory` |

因此该用例**仅能证明客户端可编译、可链接、可构造并发起调用**，不具备功能
正确性判定力。实质性验证由 `test_package/test_document_service.cpp` 承担
（真实构造客户端 + 调用两个 `SyncChunkDocument` 重载 + 断言返回状态，5/5 通过）。

## 遇到的问题与解决方案

| # | 现象 | 根因 | 解决 |
|---|------|------|------|
| 1 | `find_package(KylinAiProto)` 报找不到 `KylinAiProtoConfig.cmake` | 该包是 `libkylin-ai-system-private` 的**组件**（`cmake_file_name=KylinAiProto`），CMakeDeps 只生成顶层 `<包名>-config.cmake` | `generate()` 固定 `KylinAiProto_DIR=<dep>/share/KylinAiProto/cmake` |
| 2 | `client.cpp` 编译失败：`no member named 'always_print_primitive_fields'` | protobuf 33.x 将该字段改名为 `always_print_fields_with_no_presence` | 补丁 0003 |
| 3 | 链接失败 `R_AARCH64_ADR_PREL_PG_HI21 … z_errmsg; recompile with -fPIC` | 制品仓 `zlib/1.3.1` 为**非 PIC** 静态库（系统同名库按 R26 静态），无法被共享库吸收 | `-Wl,--exclude-libs,ALL`（harfbuzz 同法）。**未** pin PIC 版 `zlib/1.3.1.1`：那会让 `systemd/261`（精确 pin `zlib/1.3.1`）二进制失配而需源码重建，违反 R36 |
| 4 | 上游测试程序 `Error loading shared library libkylin-ai-document-service.so` | 共享库无 `DT_SONAME`，消费者按路径记 `DT_NEEDED`（`../lib….so`），加载器无法解析 | 注入 `CMAKE_SHARED_LIBRARY_SONAME_C(XX)_FLAG=-Wl,-soname,`（OHOS 无 `Platform/HarmonyOS.cmake`，该变量默认为空，见 E537） |
| 5 | 上游测试程序 `Error 127 … libsystemd.so.0 not found` | 构建树 test 可执行文件无 RPATH（OHOS 工具链下 build-tree RPATH 不生效） | `build()` 中用 `Environment()` 注入 `LD_LIBRARY_PATH`（构建树 + 各依赖 `lib/`） |
| 6 | `-DENABLE_TEST=ON` 无效，test 程序不构建 | 上游 `if (DEFINED ENABLE_TEST) unset(ENABLE_TEST CACHE)` 把 Conan 注入的 CACHE 变量中和 | 补丁 0001 调整顺序（`option()` 在前） |
| 7 | pkg-config 发现失败（`No package 'grpc++' found` / `libsystemd`） | 制品仓 `grpc.pc` 的 `Requires` 链引用未安装的 `absl_*` 模块；`systemd/261` 包 `lib/pkgconfig/` 为**空目录** | 补丁 0001 改为 `find_package(gRPC/systemd/nlohmann_json CONFIG)`（并在 `generate()` 固定 `gRPC_DIR`/`absl_DIR`/`utf8_range_DIR`，因 grpc/protobuf 为 `cmake_find_mode=none`） |
| 8 | 协议代码生成：制品仓 proto 与源码不匹配 | 制品仓 `kylin-ai-proto` 的 `document.proto` 已过期（缺 `max_doc_chars_count`/`callback_data`/`Status`），而 `client.cpp` 调用 `add_max_doc_chars_count()` | 补丁 0001 用源码树 `document.proto`（`KYLAI_GRPC_PROTOCOL_DIR=源码根`），并移除与之输出同名的 `protobuf_generate_cpp` 调用 |
| 9 | `conan package()` 写系统根失败 | 上游 4 处 `install(... DESTINATION /usr/…)` 绝对路径 | 补丁 0001 改为 `${CMAKE_INSTALL_INCLUDEDIR}` / `${CMAKE_INSTALL_DATAROOTDIR}` / `${CMAKE_INSTALL_LIBDIR}`（并补 `include(GNUInstallDirs)`） |

## 源码修改

3 个补丁，全部为可移植性修复，**未引入 `__OHOS__` 平台宏**（R8）：

| 补丁 | 文件 | 内容 |
|------|------|------|
| `0001-CMakeLists.txt.patch` | `CMakeLists.txt` | `include(GNUInstallDirs)`；pkg-config → `find_package`；proto 生成源改为源码树；安装路径绝对 → 相对；`option(ENABLE_TEST)` 顺序修正 |
| `0002-pkgconfig-relocatable.patch` | `pkg-configs/kylin-ai-document-service.pc` | 加 `prefix=${pcfiledir}/../..` 与 `-L${libdir}`/`-I${includedir}`，取代硬编码 `-I/usr/include/…` |
| `0003-protobuf33-print-options.patch` | `src/client.cpp` | `always_print_primitive_fields` → `always_print_fields_with_no_presence` |

## 依赖版本

- 直接：`grpc/1.84.0`、`protobuf/33.6`、`libkylin-ai-system-private/1.2.0.0`、
  `systemd/261`、`nlohmann_json/3.12.0`
- 传递：`zlib/1.3.1`、`openssl/3.5.6`、`abseil-cpp/20260107.1`、`c-ares/1.34.6`、
  `re2/2024-04-01`、`libcap/2.69`、`liblzma/5.8.1`、`libzstd/1.5.7`、
  `libxcrypt/4.5.2`、`libucontext/1.5.2`
- 版本约束要点：`grpc/1.84.0` 要求 `protobuf/33.6`（用 `33.6.1` 会
  `Version conflict … originates from grpc/1.84.0`，实测）
- W0 依赖发布检查：以上包均已在制品仓发布（`conan list` 逐项确认 recipe，
  `conan install --build=never` 确认 binary 可解析，R35）
- 制品仓中 `kylin-ai-document-service/1.2.0.0` 此前不存在 → 无 L0j 版本占用冲突，
  版本号保持上游 `1.2.0.0`，**未递增**（R37）；分支名 `feat/kylin-ai-document-service-1.2.0.0`
  去前缀后精确等于 `包名-版本号`，L0n 通过

## 平台注意

- OHOS **不运行 systemd 守护进程**，也无用户 D-Bus：`DocumentChunkClient`
  构造时 `sd_bus_open_user()` 失败、RPC 连接 unix socket 失败（实测
  `Failed to connect to user bus`、`errorCode=14`）。属平台能力限制，
  不影响编译、链接与库的 API 可用性；已计入兼容性说明与 MANIFEST。
- `/tmp` 只读（E002）：本库默认 socket 路径为 `/tmp/document_service_sync_<uid>.sock`，
  运行期连接前即因 `/tmp` 不可写而失败；不影响构建。
- 系统同名库检查（R26/G3）：`/lib`、`/lib64` 下**无** `libkylin-ai-document-service.so`
  → 非系统同名库，保持默认动态链接，无需静态化。
- SONAME（L5a）：产物 `libkylin-ai-document-service.so.2.0.0` 具
  `DT_SONAME=libkylin-ai-document-service.so.2`（相对名，非绝对路径）。
- 依赖注入仅落在 conan build/package 目录，**未写共享 `/usr/local`**（R49）。

## 验证结果（conan create，2026-09-26）

```
conan create . --user=ohpcd --channel=stable \
  -pr:h=~/.conan2/profiles/ohos-aarch64 -pr:b=~/.conan2/profiles/ohos-aarch64 --build=missing
→ EXIT=0
```

- 主配方：`cmake configure + build` 成功；上游测试程序 `test/test` 编译并执行（退出码 0）
- `test_package`：`======== Testing the package` 段执行，
  消费者测试 **5/5 checks passed**，产物校验（client.h / .so / .pc 存在且非空）通过
- 产物：`libkylin-ai-document-service.so{,.2,.2.0.0}`、`include/kylin-ai-document-service/`（4 头文件）、
  `share/pkgconfig/kylin-ai-document-service.pc`、`share/kylin-ai-document-service/python/`、
  `lib/systemd/user/kylin-ai-document-service.service`、`licenses/LICENSE`
---

**编译结束**: 2026-09-26 22:43
**最终状态**: pending_ci（本机 W3 全绿；按仓内约定，CI 验证前不预标 built）
