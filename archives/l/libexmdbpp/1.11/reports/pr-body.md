- **三方库名称**：libexmdbpp
- **上游版本**：1.11
- **上游仓库地址**：https://github.com/grommunio/libexmdbpp
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent 技能的知识图谱（命中 E092「CMake 不识别 HarmonyOS 平台，需由 Conan 工具链注入平台信息」、E017「GitHub 源临时镜像注入」），未命中部分已按 notes.md 记录

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 来源：上游无 tests/ 目录，CMakeLists.txt 无 `enable_testing()`/`add_test()`，`ctest -N` 无注册用例 |
| 集成测试 | 0 | 来源：同上，源码包 21 个文件全部为 CMake 配置/头文件/库源文件/LICENSE |
| 其他测试 | 0 | 源码树中不存在任何 `*test*.cpp` 文件，也无 `make check` 目标 |
| **合计** | **0** | 上游测试用例 **N = 0**，清点证据见 `test_package/MANIFEST.yml` 与 `notes.md` |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游本身没有单元测试可供移植 |
| 集成测试 | 0 | 不变 | 上游本身没有集成测试可供移植 |
| 鸿蒙特有测试 | 7 个用例 / 55 项断言 | 新增 | `test_package/test.cpp`：3 个**真实 socket 端到端回路** + 4 个 API 级用例 |
| **合计** | **7 个用例 / 55 项断言** | **+7 / +55** | 上游 N=0，全部为适配后新增 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 上游 1.11 发布包中完全不存在测试用例，因此不存在对上游测试的修改。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> - **补全的测试范围**：7 个用例 / 55 项断言，全部是**完整消费者用例**（构造输入 → 真实执行 → 产生输出 → 校验内容），其中 3 个跑在**真实 TCP socket** 上：
>   1. **e2e-1** `GET_STORE_PROPERTIES`：测试进程内起 exmdb server 模拟器（`AF_INET`/`127.0.0.1`，端口由内核分配），`ExmdbClient` 真实 `connect()` + ConnectRequest 握手 + 发送请求；模拟器解析它**实际收到的字节**并回帧；客户端反序列化 `PropvalResponse`。校验：2 个 propval 的 tag/type/toString，以及线上帧数、callId、homedir、cpid、proptag 列表（15 项）
>   2. **e2e-2** 协议错误传播：模拟器第二次应答 `MISCONFIG_PREFIX`，校验库抛出的 `ExmdbProtocolError` 及其 `code` 字段（2 项）
>   3. **e2e-3** `GET_STORE_ALL_PROPTAGS`：新连接发送 `GetAllStorePropertiesRequest`，校验 `ProptagResponse` 的 3 个 proptag 与线上 callId（6 项）
>   4. `exmdbpp::util` —— `valueToGc`/`gcToValue` 往返、`makeEid`/`makeEidEx`、`ntTime`/`nxTime`（FILETIME ↔ UNIX 时间）换算（5 项）
>   5. `exmdbpp::structures::TaggedPropval` —— LONG/STRING/BYTE 属性的 tag/type/count/typeName/toString 与拷贝构造深拷贝语义（15 项）
>   6. `exmdbpp::structures::Restriction` —— `EXIST()` 构造、`operator bool` 判定、`serialize()` 输出字节序列（`08 03 00 FF 0F`，长度 5）（8 项）
>   7. `exmdbpp::requests::GetStorePropertiesRequest::write()` —— RPC 报文总长度、首字节 CallId、homedir 字符串编码（4 项）
> - **为什么要有真实 socket 回路**：本库是纯客户端库，其核心价值（建链/握手/序列化/响应解析/错误传播）只有真正收发字节才能验证；设备侧没有 gromox 的 `exmdb_provider`，因此在测试进程内按库自身的帧格式（`[len:u32LE][callId][payload]` / `[status][len:u32LE][payload]`）实现等价模拟器。
> - **补全原因**：上游仅交付库源码与 Doxygen 文档，无任何正式测试框架；鸿蒙适配需提供可回归的消费者级验证。为避免 `-DNDEBUG` 下 `assert()` 被剔除导致测试退化为恒返回 0 的空壳，统一采用自定义 `CHECK` 宏（普通 if 语句），全程不使用 `<cassert>`。
> - **新增测试文件清单**：
>   1. `test_package/test.cpp` — 消费者测试主程序，7 个用例 / 55 项 CHECK 断言，任一失败即返回非 0
>   2. `test_package/CMakeLists.txt` — C++17 工程，`find_package(libexmdbpp REQUIRED)` 并链接 `libexmdbpp::libexmdbpp`（端到端用例需 `Threads::Threads`）
>   3. `test_package/conanfile.py` — 构建后以 `conanrun` 环境真实执行二进制（动态库经 LD_LIBRARY_PATH 解析）
>   4. `test_package/MANIFEST.yml` — 上游测试清点证据、用例清单与断言计数（55）

## 验证结果

- 编译状态：通过（`conan create` G1 配方完整性 / G2 干净构建 / G3 系统同名库隔离 / G4 产物完整性全部 PASS；W3 本地 CI 模拟 L0-L5 全部 pass，包 ID `01d92cf349a0dd98ff915f4bd99a04430171517f`）
- 上游测试用例通过率：0/0（不适用，上游 1.11 发布包内不存在测试；清点证据见 MANIFEST.yml）
- 新增测试用例通过率：7/7 用例、55/55 断言（100%），实测输出 `test_libexmdbpp: 7 cases, 0 failed (55 checks, 0 failures)`

## 补充说明

1. **两个源码补丁**：
   - `patches/0002-src-requests.cpp.patch`：musl 未定义 glibc 的 typedef `ulong`，改写为标准 `static_cast<unsigned long>`（会话 ID 随机数引擎播种用）。改动与平台无关，补丁中未引入 `__OHOS__` 等平台宏。
   - `patches/0001-CMakeLists.txt.patch`：CMake 无 Platform/HarmonyOS 模块，`CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG` 为空导致链接器收不到 `-soname`，产物缺少 DT_SONAME；补丁给共享目标追加 `LINK_FLAGS "${CMAKE_SHARED_LINKER_FLAGS} -Wl,-soname,libexmdbpp.so"`。
2. **导出 CMake 目标的 SONAME 同步**：仅补链接标志时 CMake 仍会在 `exmdbppTargets-release.cmake` 写 `IMPORTED_NO_SONAME TRUE`，因此 `package()` 在安装后把该项换成 `IMPORTED_SONAME_RELEASE "libexmdbpp.so"`（与 ELF 中实际 DT_SONAME 一致）。另一条可行的路线是全局注入 `CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG`（仓库内 coin3 4.0.7 同法），但它会使产物变成 `.so.0` + namelink 软链，而 `conan create` 在构建目录创建该软链必报 `Permission denied`，故选用单文件路线。
3. **构建日志落盘**：OHOS 上 clang 的诊断经 conan 捕获输出流时会被吞掉（make 只报 `Error 1`、无 `error:` 行），配方与 test_package 的 `build()` 均改用 `cmake.build(stdout=log, stderr=log)` 将输出绑定到 `<build_folder>/build.log`，失败时回灌日志尾部。
4. **仅动态库**：上游 `CMakeLists.txt` 硬编码 `add_library(exmdbpp SHARED ...)`，无静态代码路径，因此配方 `shared` 默认为 True 且通过 `validate()` 拒绝 `shared=False`。
5. **Python 绑定未启用**：`BUILD_PYEXMDB=OFF`，`pyexmdb` 需 pybind11 + Python 开发头文件，不在本次适配范围。
6. **端到端的边界**：3 个 e2e 用例已在真实 TCP 上验证建链、握手、请求序列化、响应解析与协议错误传播；设备侧没有 gromox 的 `exmdb_provider`，故用测试进程内的协议等价模拟器替代，未做与真实 grommunio 服务端的互操作测试。
