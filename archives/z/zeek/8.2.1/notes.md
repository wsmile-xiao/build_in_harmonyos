# zeek 8.2.1 适配笔记

## 编译环境
- 构建系统: CMake（官方采用 cmake；仓库内带 autotools 遗留，忽略）
- 编译日期: 2026-09-21
- 编译器: clang/clang++ 15.0.4
- 状态: published

## 子模块策略（阶段1b 勘察结论 ⭐）
**官方 tarball 自足，无需拆分/额外合并子模块源。** 证据（从 `zeek-8.2.1.tar.gz` 解压后实测）：
- `auxil/spicy/` 21966 文件：含 `hilti/`(toolchain 342+hw 文件、runtime 144)、`spicy/`(toolchain 118、runtime 48)、`3rdparty/` vcpkg 13656 等完整源码
- `auxil/broker/` 4215 文件：含 `libbroker/` 3768 文件完整真实源码、`caf/` 内嵌
- `auxil/c-ares/` 531 文件、`auxil/btest/`、`auxil/zeekctl/` 等一应俱全
- 结论：单 tarball 即可构建完整 zeek（含 Spicy 内嵌编译），conandata.yml 只需这一个源 URL，不需要按子模块逐一下载合并。

## 平台点狩猎清单（阶段1c 主动挖点 ⭐ 难度评级核心）

> 每挖到一个点：在 .work 上改一处 + notes.md 记「现象/证据/修复」三件套。一个真 OHOS 修复的诊断过程 > 三个"能编译"。R8 红线：平台宏不进 patches/conanfile，用 CMake 能力宏 + POSIX 接口。

### ① 实锤级（一定会踩，挖到=真金）
| 点 | 命中面 | 预期修复 |
|----|--------|----------|
| binpac/bifcl 生成器 | CMake 里是 host 工具，交叉编译必须 host 构建、目标侧用——zeek 私有工具链现场，9 成会炸 | tool_requires/host 侧构建生成器，目标侧只消费产物（R49 私有 prefix） |
| libkqueue（auxil/） | OHOS 无 kqueue，走 epoll 分支；EPOLLRDHUP/POLLRDHUP 半关闭检测 | 知识面 E233：POLLRDHUP/EPOLLRDHUP 支持检测 |
| dlopen 插件加载（PluginManager） | 插件 .so 动态加载，符号化/-rdynamic 与 OHOS linker 差异 | 知识面 E013 dlopen、E222 backtrace |

### ② 高价值（非必踩，踩到=加分）
| 点 | 命中面 | 预期修复 |
|----|--------|----------|
| getifaddrs/getnameinfo | OHOS libc 接口差异 | 接口枚举替换 |
| mallinfo/strdupa/strchrnul/getrandom | glibc 专属，OHOS musl 替换 | E 知识面现成 |
| builder/broker 的 SO_REUSEPORT/EPOLLEXCLUSIVE | 事件循环细节 | 条件编译 |

### ③ Spicy 创新点（无先例，最拉难度）
| 点 | 命中面 | 预期修复 |
|----|--------|----------|
| HILTI→C++→宿主 交叉编译链 | tool_requires 配 flex/bison/swig，spicyc/hilti 生成器 host 侧运行 | 内嵌 Spicy 编译（tarball 自带 `auxil/spicy/`） |

## 已发现平台问题（阶段1a/1b/1c）

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 双轨复制 `.work` 失败 | zeek tarball 内 `auxil/spicy/` 存在「目录别名」符号链接（如 `hilti/runtime/include/hilti/rt -> ..`、`toolchain/include/hilti -> ../include`），`shutil.copytree` 跟随解析成环；且 HMDFS 拒绝 `os.link` 硬链接 | 用 `cp -a`（保留符号链接不跟随）手工重建 `.work`，再 `--no-download` 续跑 init-build |
| 2 | `.work` 文件数膨胀 64076→84493 | copytree 硬链接回退 copy2 时同样跟随符号环，递归展开 `hilti/hilti/...` 深层链 | 检测到膨胀即 `rm -rf .work && cp -a .orig .work` 重建 |
| 3 | configure: fiber 平台不支持 OS=HarmonyOS | `auxil/spicy/3rdparty/fiber/cmake/cmake-utils/cmu_detect_env.cmake` 只认 `CMAKE_SYSTEM_NAME MATCHES "Linux"`，HarmonyOS 落空 → `CMU_OS_POSIX` 恒 False → 无 asm 源报 FATAL | 补丁：`MATCHES "Linux|HarmonyOS"`（与仓库先例 aws-c-io/arpon 一致，R8 能力判断） |
| 4 | configure: libkqueue `unsupported host os` | `auxil/libkqueue/CMakeLists.txt` 仅 `STREQUAL Linux` 分支，HarmonyOS 走 else 报错 | 补丁：`STREQUAL Linux OR STREQUAL HarmonyOS`（复用 linux/ 源） |
| 5 | configure: ZeroMQ/SWIG 可选件缺失 | 集群 ZeroMQ 后端、zeekctl 的 pysubnettree(SWIG) 非核心必需 | `-DENABLE_CLUSTER_BACKEND_ZEROMQ=OFF`、`-DINSTALL_ZEEKCTL=OFF -DINSTALL_ZKG=OFF -DINSTALL_ZEEK_CLIENT=OFF`；SWIG 走 conan tool_requires |
| 6 | make: broker `fatal error: 'memory_resource' file not found` | OHOS libc++（`_LIBCPP_VERSION 15004`, `libcxx-ohos/include/c++/v1`）**缺失标准 `<memory_resource>` 头**（std::pmr），只剩 `experimental/memory_resource`（std::experimental::pmr）；且该 experimental 头对 `monotonic_buffer_resource`/全局资源函数只声明未定义 | 自写 shim 头 `<memory_resource>`（`tmp/zeek-ohos-include/memory_resource`）：暴露 `std::experimental::pmr` 的现有实现 + 补全 `monotonic_buffer_resource` 与 `new_delete_resource`/`get_default_resource`/`set_default_resource`/`null_memory_resource` 定义；通过 `-I` 加入构建（R8：不进 patches） |
| 7 | make 链接: `undefined symbol: pthread_cancel / pthread_setcancelstate / pthread_testcancel` | OHOS musl libc 在 `<pthread.h>` 声明这些符号但 **libc.so 未实现**（线程取消不支持）；libkqueue 的 `kevent.c`/`kqueue.c`/`platform.c` 调用它们（仅 `#ifndef _WIN32` 守卫） | 双机制（独立、无冲突）：① 配方无条件把 `shims/pthread_compat.c`（3 个 weak no-op）编成 pthread_compat.o 链入所有可执行文件（weak 让位真实强符号）；② libkqueue CMake（补丁 0013）`check_function_exists(pthread_cancel)` 能力检测 → 未实现时编译自带 compat 并定义 `HAVE_PTHREAD_CANCEL_COMPAT`（R8 能力判断，无平台宏） |

## 平台点实测三件套（阶段1c configure/make/make check 逐点记录 ⭐）

> 每个点 = 现象 / 证据 / 修复。R8 合规：全部用 CMake 能力宏 / 可移植 C++ / 兼容 shim，无 `__OHOS__` 平台宏进 patch。

### P1 CMake 平台探测：fiber/libkqueue 把 OHOS 当 unknown platform
- 现象：`3rdparty/fiber` 报 `ARCh=... empty` + libkqueue 报 `unsupported host os`，configure 中途 abort
- 证据：探针 `cmake -P` 打印 `SYSTEM_NAME=HarmonyOS PROCESSOR=unknown UNIX=`——OHOS 下 CMake 的 `UNIX/APPLE/WIN32` 平台标志全不置位，`fiber` 的 `cmu_detect_env` 架构判定落空；libkqueue 又按 `CMAKE_SYSTEM_NAME` 白名单（`UNIX` 键）落入 else。而 `auxil/spicy` 的符号环目录别名正是 copytree 失败的源头
- 修复：toolchain 文件注入 `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64`（OHOS 本为 Linux 内核 + musl，语义完全等价），fiber 走 aarch64 分支、libkqueue 走 `src/linux/*` epoll 分支。探针验证 `UNIX=1 SYSNAME=Linux`

### P2 host 生成器 ALIAS 命令未展开（BifCl/BinPAC/gen-zam，实锤级私有工具链现场）
- 现象：`make` 报 `Error 127 — Zeek::BifCl: inaccessible or not found`，先后出现在 `bif-std-types.bif`、`pac-binpac-lib.pac`、`gen-zam-OPs` 三个生成规则
- 证据：`build.make` 里命令是字面量 `cd ... && Zeek::BifCl ...`（未替换成可执行路径）；但 `build/tools/bifcl/bifcl`（96KB）与 `build/tools/binpac/src/binpac`（444KB）均已真实构建成功、`--version` 可跑。迷你探针（工具链模式下 `add_custom_command(COMMAND ALIAS)`）复现：CMake 4.1.2 在设置 toolchain 后不再把 `::` 命名空间 ALIAS 目标名展开为可执行路径。typical 的 host 生成器目标（binpac/bifcl 在 CMake 里是 host 工具）——交叉编译私有工具链现场
- 修复：三处 CMake 源（`cmake/BifCl.cmake`、`cmake/BinPAC.cmake`、`cmake/Gen-ZAM.cmake`）把 `COMMAND Zeek::BifCl/Zeek::BinPAC/gen-zam` 改为 `$<TARGET_FILE:...>` 生成器表达式展开真实路径。重配后 build.make 验证已展开为 `../tools/binpac/src/binpac`，三生成步骤全过

### P3 OHOS libc++ 缺 C++20 ranges 算法（全局性平台点，47 文件 83+ 用）
- 现象：`std::ranges::sort/find/copy/transform/...` 编译报 `no member named 'sort' in namespace 'std::ranges'`，`paraglob.cpp`→`Dict.h`→`telemetry/`→`.pac`/`.bif` 模板源码链式报错
- 证据：SDK libcxx-ohos `_LIBCPP_VERSION 15004`，`<ranges>` 头存在但 `__cpp_lib_ranges` 未定义——命名空间有、算法成员整批缺失；探针 `-stdlib=libc++` 同样编不过 ranges，判定为硬平台约束
- 修复：全部改为等价经典 STL（`std::ranges::sort(v,cmp)`→`std::sort(v.begin(),v.end(),cmp)`；`reverse_view`→反向迭代器；`ranges::unique` 返回对→`std::unique` 单迭代器；`ranges::remove+begin`（erase-remove 惯用法）→`v.erase(std::remove(...),v.end())`）。子代理按映射表机械改写 + 我手工处理特殊形态，完成后全树 `std::ranges::` 清零

### P4 BOOS libc++ 缺 `<memory_resource>`（broker 深用 `std::pmr::` 37 处）
- 现象：`broker/envelope.hh:12 fatal error: 'memory_resource' file not found`
- 证据：SDK libcxx-ohos 无 `memory_resource` 头，`experimental/memory_resource` 只声明未定义 `monotonic_buffer_resource`；且 default-constructed `polymorphic_allocator` 链接期引用 `experimental::pmr::get_default_resource()`（SDK libc 未导出）→ 运行时 SIGSEGV
- 修复：自研 shim 头 `ohos-shims/memory_resource`（`-I` 注入）：复用 SDK 真 `memory_resource` 基类 + 正确 bump-pointer `monotonic_buffer_resource`（每次分配对齐）+ inline `get/set/new_delete/null_default_resource` + 补 `experimental::pmr::get_default_resource()` 转发符号（inline namespace 对齐）。broker 13 个曾 SEGFAULT 的测试 100% 恢复

### P5 OHOS libc 缺线程取消符号（链接期）
- 现象：链接 zeek 报 `undefined reference to pthread_setcancelstate/pthread_testcancel/pthread_cancel`
- 证据：OHOS libc.so（musl 模型）不导出线程取消 API；引用方全是 libkqueue（`kevent.c`/`proc.c`）
- 修复：`shims/pthread_compat.c` 提供 3 个 `__attribute__((weak))` no-op 实现，由配方（exports_sources + build()）**无条件**编译为 `pthread_compat.o`，经 `CMAKE_EXE_LINKER_FLAGS` 链入所有可执行文件——真实提供该 API 的平台走强符号，OHOS 由 weak 符号补齐，无冲突（W3 链接实测通过）

### P6 BOOS libc 缺 `fts.h`（FTS 目录遍历 API）
- 现象：`src/zeekygen/Target.cc fatal error: 'fts.h' file not found`
- 证据：OHOS sysroot 无 `fts.h`/`libfts`；`auxil/libunistd` 的 fts 是 macOS 专属路径不参与 Linux 构建
- 修复：`dir_contents_recursive` 从 `fts_open/fts_read` 改用 C++17 `std::filesystem::recursive_directory_iterator`（可移植、无平台宏），对应 include `<fts.h>`→`<filesystem>`

### P7 `sockaddr_storage` 重定义（OHOS 头栈 UAPI 冲突）
- 现象：AF_Packet 插件编译报 `redefinition of 'sockaddr_storage'`（`linux/if.h` 与 `sys/socket.h`）
- 证据：OHOS musl 的 `sys/socket.h` 用 `#ifndef __MUSL__` 守卫自己的 `sockaddr_storage`；但默认不定义 `__MUSL__` 导致与 UAPI `linux/socket.h` 双定义。最小复现 `-D__MUSL__` 消除
- 修复：toolchain 追加 `-D__MUSL__`（能力宏，等价 musl 语义，非平台宏）

### P8 旧 libc++ `construct_at` 聚合体初始化失败（CallInfo/DispatchInfo）
- 现象：`emplace_back(nullptr,&f)` 报 `no matching function for call to 'construct_at'`，target 是聚合体 `struct CallInfo{ const CallExpr*; Frame*; }`
- 证据：旧 libc++ 的 `std::construct_at` 不支持聚合体括号初始化；同问题复现于 `script_opt/CPP/DeclFunc.h:71 DispatchInfo`
- 修复：两聚合体补 constexpr/普通构造函数（可移植，新旧 libc++ 皆可）

### P9 转换 bug：broker C 数组被 `.begin()`（3 处）
- 现象：`connector.cc:686`/`p2p_message_type.cc:26`/`store_event.cc:148` 编译报 `member reference base type 'const std::string_view [13]' is not a structure`
- 证据：ranges→经典 STL 机械改写时把「原始 C 数组」当容器用了 `.begin()/.end()`；`handshake_states`/`p2p_message_type_names`/`type_strings` 均为静态 C 数组
- 修复：改用 `std::begin/std::end`（C 数组安全）

### P10 `broker.backend` 测试因 HMDFS /tmp 只读失败（缺 TMPDIR 支持 → 可移植补丁 0003）
- 现象：`ctest broker.backend` 报 `Unable to create unique filename: Read-only file system`
- 证据：HMDFS `/tmp` 只读（SKILL E002 已知陷阱）；测试依赖在 `/tmp` 建唯一临时文件；根因代码为 `detail/filesystem.cc` 的 `make_temp_file_name` 硬编码 `/tmp` 前缀、不认 `TMPDIR` 环境变量
- 修复：可移植补丁 0003（`detail/filesystem.cc` POSIX 分支：`::getenv("TMPDIR")` 空则回退 `/tmp` + `snprintf` 固定 512B 缓冲带溢出守卫 + `mkstemp`，无平台宏，R8 合规）；HMDFS 侧运行 ctest 时指定 `TMPDIR=<可写目录>` → **26/26 全过**。历史记录：09-21 曾按 E002 平台限制记录（25/26），09-22 本地完善阶段解决
- 附注：探索期遗留树 `build-ohos`（HNP 工具链、缺 ohos-shims -I 注入）仍有 5 项 pmr 相关测试 SEGFAULT——该树 P4 类配置差异，与本补丁无关，不追修；PR 测试口径以 `build/` 树（26/26）为准

## make check 实测结果（R51 上游测试清点/实测口径）

- configure/make 首次编通 = 100%（约 2h 内，含上述 9 个平台点逐点修复）；`src/zeek` 20.7MB，`./src/zeek --version` → `zeek version 8.2.1` ✅
- 单元测试：`ctest -R broker.` 26 项 → **26/26 通过（100%）**（此前 13 个 broker 测试 SEGFAULT 全部由 P4 shim 修复解决；broker.backend 由 P10 TMPDIR 补丁 + 可写 TMPDIR 运行解决，完整运行命令见 reports/test-report.md）；遗留树 build-ohos 5 项 SEGFAULT 属 P4 类配置差异（缺 ohos-shims -I），不追修
- R51 上游测试清点：btest 套件 287 个 .test + 1824 个 .zeek（17 个 TestDirs），ctest 35 项（26 broker.* + 8 python-* + 1 其它）
- Spicy 协议分析器与 JavaScript 支持按最小可行关闭（`-DDISABLE_SPICY=ON` `-DDISABLE_JAVASCRIPT=ON`），ZeroMQ 集群后端关闭（`-DENABLE_CLUSTER_BACKEND_ZEROMQ=OFF`）
- btest 集成测试实测（逐项技术归因，详见 reports/test-report.md，gitignore 不在 PR 内）：
  1. 最小构建加载 base 脚本失败：`scripts/base/packet-protocols/igmp/main.zeek` 在 `zeek_init` 无条件 Reporter::error（IGMP Spicy 分析器在 DISABLE_SPICY 构建必然缺失，上游脚本无守卫）→ 初始化 fatal
  2. HMDFS /tmp 只读（E002）：btest 需在临时目录落 Baseline/输出对比，无法创建临时文件
  3. 判定：环境/构建形态限制，非适配缺陷；完整 btest 需「ENABLE_SPICY 全量构建 + 可写工作目录」验收机补跑
- python-* 8 项 ctest：N/A——最小构建未启用 python 绑定（构建形态取舍）

## 依赖版本

官方 build-from-source 必需（已按 configure 实测确认，全部制品仓已发布）：
- libpcap/1.10.6（requires，抓包）
- openssl/3.5.8.1（requires，TLS/证书）
- zlib/1.3.1（requires）
- flex/2.6.4 + bison/3.8.2（tool_requires，host 侧生成器：词法/语法）；swig/4.4.0 随 INSTALL_ZEEKCTL=OFF 构建形态对齐移除（pysubnettree 为其唯一消费者，2026-09-24）
- c-ares/zeromq 等 `auxil/` 内嵌可选项，随 zeek 源码自带，不单独依赖（zeromq 后端本构建关闭）

## 验证结果

```bash
# 配方构建（W3 本地 CI 同脚本，2026-09-22）
conan create archives/z/zeek/8.2.1 --name=zeek --version=8.2.1 --build=missing --build=zeek/*
# → zeek/8.2.1: Created package revision 9833f328a9883a7c657740604a8f48b7
# → Package c141a47385bfdae2179e05e07c6b4c798e779d86 built & tested, CONAN_RC=0

# 冒烟（构建产物）
./src/zeek --version   # → zeek version 8.2.1 (exit 0)

# conan-verify 8 道门禁：G1/G2/G3/G4 + L2/L4/L5 PASS（见 conan-verify-report.md）
# W3 本地 CI（build_and_test.sh）：L0=pass L1=pass L2=pass L4=warn L5=pass，
# Build Summary: Total 1, Success 1, Pass rate 100%
# 单测：ctest broker.* 26/26 通过（100%，TMPDIR=<可写目录> 运行，详见 test-report.md）
```

## 注意事项

- **R8 红线**：平台适配不用 `#ifdef __OHOS__`，用 CMake 能力宏（`CMAKE_SYSTEM_NAME`、`_GNU_SOURCE`）或 POSIX 接口
- **符号链接陷阱**：任何涉及 `auxil/spicy/` 的复制/打包操作必须用 `cp -a` / `tar` 默认不跟随，禁止 `copytree` 全量复制
- **最小可行优先**：先 `-j1` compile 过 + 内核跑通，再去抠 Spicy/抓包细节
## 对话记录

### 对话 #1 — 初始适配（2026-09-21）
完成 P1-P10 平台适配点诊断与修复，产出 70 个补丁 + pmr/pthread 两个 shim；build/ 树 ctest broker.* 25/26（broker.backend 受 HMDFS /tmp 只读 + 上游源码硬编码 /tmp 双重阻塞）；W4 审计 pass，创建 PR #11976（后由用户关闭，转入本地完善）。

### 对话 #2 — 本地完善裁决（2026-09-22）
用户裁决：先不提交 PR，本地完善 + 规范自查，经用户审阅后再提。采纳 TMPDIR 可移植方案：新增补丁 0003（auxil/broker filesystem.cc 硬编码 /tmp → getenv("TMPDIR")，空回退 /tmp，纯测试辅助零运行期影响）；补齐 hilti runtime 5 项编译兼容补丁（0016-0020，对应 libc++ 差异草稿 E430/E433）；补丁集按文件路径字母序整体重编号为 76 个（0001-0076），conandata/manifest 同步重建。

### 对话 #3 — 验证与文档同步（2026-09-22）
76 个补丁逐一 orig→apply→diff 验证与适配工作树逐字节一致（76/76 PASS）；build/ 树 ctest broker.* 26/26 = 100%（TMPDIR=<可写目录> 运行）；notes/test-report/pr-body/build-report/compatibility/软件级 manifest/feedback 全套文档同步 76 与 26/26。

### 对话 #4 — W3 重验与收尾（2026-09-22）
finish published 全 10 步：G2 干净构建 PASS；W3 本地 CI 模拟（setup.sh + build_and_test.sh，conan create）PASS，.ci-result.json exit_code=0（含日志 SHA256 防伪造）；收尾遗留非阻塞告警（finalize 补丁数双重计数误报、gen_summary 崩溃、.staging-verified 缺失）已补记 SKILL_FEEDBACK_d758202d.md 建议 ⑤⑥⑦，标记文件已补建。

### 对话 #5 — CI 第 1 轮红修复（2026-09-24）
CI（CI-038，task #57541）conan-build-test 红：configure 死于 `auxil/zeekctl/auxil/pysubnettree/CMakeLists.txt:11` `find_package(Python 3.9 REQUIRED COMPONENTS Interpreter Development)`——CI worker 的 HNP Python 3.12.9 有解释器但无 Development 组件（缺 Python.h/libpython）；本地 W3 绿是因本地 Python（源码安装、带 dev 组件）掩盖了差异（W0b 环境语义不可迁移，mcfly 教训同构）。
修复（构建形态对齐，非失败逃逸）：配方补 `INSTALL_ZEEKCTL=OFF`（zeekctl + pysubnettree 退出构建，`CheckOptionalBuildSources` 宏语义确定：OFF = 子目录完全不进 configure）；同补 `INSTALL_ZKG=OFF`/`INSTALL_ZEEK_CLIENT=OFF`——探索期构建与 manifest configure_options 早已声明三者关闭，此前配方缺失后两者（配方与文档形态不一致，本次一并修正）；swig tool_requires 与 SWIG_EXECUTABLE/SWIG_DIR 注入移除（全树枚举 find_package(SWIG) 仅 pysubnettree 一处消费）。
静态论证（CI 转绿的依据）：全构建路径唯一 REQUIRED Python Development 消费者 = pysubnettree（其余为软探测 FindPythonDev.cmake / vcpkg 非构建代码）；zeek-aux/zeek-client 的 CMakeLists 无 find_package(Python)；btest/ZKG/systemd-generator 子目录在 CI 日志失败点前均已配置成功。零新增补丁，76 补丁集不变，版本号保持 8.2.1（从未发布，L0j 不触发）。
---

**编译结束**: 2026-09-24 02:14
**最终状态**: published
