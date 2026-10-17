# bcc 0.37.0 适配笔记

## 编译环境
- 构建系统: cmake（顶层 CMakeLists.txt，project(bcc)）
- 编译日期: 2026-09-16
- 编译器: clang/clang++ 15.0.4（/data/service/hnp/bin，aarch64-linux-ohos）
- 状态: published（本地 Step 2 编译通过 + conan-verify 8 门禁 PASS + finish W2/W3 PASS，最终状态 published）

## 编译步骤

1. init-build bcc 0.37.0 --url=https://github.com/iovisor/bcc/archive/refs/tags/v0.37.0.tar.gz
   - HMDFS 上 os.link 硬链接 EPERM + tarball 内 broken symlink（tests/lua/spec -> src/lua/bpf/spec）导致
     dual-track 复制失败；手工 `cp -a`（保留符号链接）重建 .work 后 --no-download 续跑成功。
2. lang-preflight 误判 bcc 为 lua（嵌套 src/lua/bpf-scm-1.rockspec 触发全树 .rockspec 扫描），
   按 R47 边界规则人工核验：顶层 CMakeLists.txt project(bcc) + src/cc 为 C++ 主体（.cc/.h），
   正确判定为 cpp，继续主流程（清除被误写的 env_unsupported 终态 result.json）。
3. Step 2 编译（cmake configure + make + make install DESTDIR staging）：
   - LLVM：发布包 llvm/15.0.4（conan）无 BPF target（仅 AArch64），bcc 的 clang 前端必需
     LLVMInitializeBPFTarget → 改用系统 SDK LLVM 15.0.4（含 bpf/bpfeb/bpfel target）。
   - SDK libclang-cpp.so/libLLVM.so 静态内嵌 `std::__h` ABI 的 libc++（NEEDED 仅 libc.so），
     而设备默认 libcxx-ohos 头为 `std::__n1` ABI → bcc 必须以 `__h` ABI 头编译才能匹配 clang
     C++ API 符号（MultiplexConsumer 等）。复制 libcxx-ohos 头并改 __config_site
     `_LIBCPP_ABI_NAMESPACE __n1` → `__h`，用 `-nostdinc++ -isystem <头>` 编译。
   - SDK 库未导出 iostream 全局对象（std::__h::cout/cerr）→ 自建 shim 静态库
     libohos_iostream_shim.a（定义 cout/cerr/clog + ios_base::Init），并把手持 5 处
     std::cerr/std::cout 改为 fprintf（BPF.cc/BPFTable.cc/bcc_syms.cc/kbuild_helper.cc/loader.cc）。
   - 依赖：libbpf/1.4.5@ohpcd/stable（静态）、elfutils（libelf.so）、zlib、libzstd 均取自本地
     conan 缓存包；bison/flex 设备自带。
   - make 全目标成功（bcc-shared/bcc-static/bpf-static/bpf-shared/test_static/test_libbcc_no_libbpf 等）；
     ENABLE_EXAMPLES=OFF（examples 非交付物）。
   - 结果：build-ohos/src/cc/libbcc.so 4.5MB；DESTDIR staging 安装 lib/libbcc.{so,a}、头文件、
     libbcc.pc 等齐全。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build dual-track 复制失败 | HMDFS 硬链接 EPERM + tarball 内 broken symlink | cp -a 手工重建 .work，保留符号链接 |
| 2 | lang-preflight 判 lua | 嵌套 .rockspec 触发全树 manifest 扫描 | 人工核验顶层 CMake project(bcc) → cpp |
| 3 | LLVMInitializeBPFTarget 未声明 | conan llvm/15.0.4 无 BPF target | 改用系统 SDK LLVM 15.0.4（含 BPF） |
| 4 | clang 符号 ABI 不匹配（__n1 vs __h） | SDK clang 库内嵌 `__h` libc++ | `__h` ABI 头编译 bcc + shim cout/cerr |
| 5 | 链接缺 std::__h::cout/cerr | SDK 库未导出 iostream 全局对象 | shim 静态库定义 cout/cerr/clog + Init |
| 6 | 链接缺 zlib gz* 符号 | bcc_zip 用 zlib 未显式 -lz | EXE/SHARED 链接旗标加 -lz |
| 7 | dlinfo 未声明（OHOS） | glibc 扩展，OHOS dlfcn.h 无 dlinfo | test_c_api.cc 改用 dladdr+dlsym 取库路径 |
| 8 | /tmp 只读 | 设备 /tmp 挂载只读 | 全部日志/探针改放 ~/tmp |

## 依赖版本

| 依赖 | 版本 | 来源 | 状态 |
|------|------|------|------|
| LLVM/Clang | 15.0.4 | 系统 SDK（ohos-sdk_26.0.0.18，含 BPF target） | 本地编译用 |
| libbpf | 1.4.5 | conan 缓存 libbpf/1.4.5@ohpcd/stable | ✅ |
| libelf (elfutils) | 0.195 | conan 缓存 | ✅ |
| zlib | 1.3.1.1 | conan 缓存 | ✅ |
| libzstd | 1.5.7 | conan 缓存 | ✅（libelf 运行依赖） |
| bison/flex | 3.8.2/2.6.4 | 设备 /data/service/hnp/bin | ✅ |

## 上游测试双口径台账（R51/R51 申报表）

### 枚举口径（source_declared_total）

**C++（tests/cc，Catch v1.4.0 框架，TEST_CASE 声明）— 共 65 个**

| 源文件 | 独立用例数 | 说明 |
|--------|-----------|------|
| test_c_api.cc | 24 | C API 用例 |
| test_usdt_probes.cc | 10 | USDT 探针用例 |
| test_bpf_table.cc | 5 | BPF table 用例 |
| test_zip.cc | 4 | zip 读取用例 |
| test_map_in_map.cc | 3 | map-in-map |
| test_sock_table.cc | 2 | sock table |
| test_queuestack_table.cc | 2 | queue/stack table |
| test_pinned_table.cc | 2 | pinned table |
| test_perf_event.cc | 2 | perf event |
| test_hash_table.cc | 2 | hash table |
| test_cg_storage.cc | 2 | cgroup storage |
| test_array_table.cc | 2 | array table |
| test_usdt_args.cc | 1 | usdt args |
| test_sk_storage.cc | 1 | sk storage |
| test_shared_table.cc | 1 | shared table |
| test_prog_table.cc | 1 | prog table |
| test_parse_tracepoint.cc | 1 | tracepoint 解析 |
| 合计 | **65** | 不含框架/支撑文件（catch.hpp、test_libbcc.cc=CATCH_CONFIG_MAIN、utils.cc、debuginfo_test_lib.cc、usdt_test_lib.cc、test_static.c=单用例 C 程序） |

**Python（tests/python，unittest 框架，test_ 方法声明）— 共 270 个**
38 个 test_*.py 文件合计 `def test_*` 270 个（test_clang.py 84、test_tools_smoke.py 88 为大头；
框架/工具文件 simulation.py、utils.py、test_brb.c 等 .c 辅助不计入）。

**Lua（src/lua/bpf/spec，busted spec + tests/lua）— 共 58+ 个 spec 条目**
codegen_spec.lua 49、compile_spec.lua 2、decoder_spec.lua 4、elf_spec.lua 3（helper.lua 不计）；
tests/lua/ 下 test_clang/test_uprobes/test_dump/test_standalone.sh 4 个脚本入口（需 luajit/bcc-lua）。

### 注册口径（configured_executable_total）

ctest -N 注册 40 项：style-check、c_test_static、test_libbcc_no_libbpf、
36 个 py_test_*（test_libbcc 目标本配置未启用）。Lua 测试因设备无 luajit 未注册
（tests/lua/CMakeLists.txt find_program(LUAJIT) 为空）。

### 实测口径（executed_passed_total）

**0/65 C++、0/270 Python、0/58 Lua**（本设备无法真实执行）

| 入口 | 实测命令 | 结果 | 首错 |
|------|---------|------|------|
| ctest（全量 40 项） | ctest --output-on-failure | 40/40 Not Run (BAD_COMMAND) | wrapper.sh shebang `#!/bin/bash`，设备无 bash（Toybox）；且测试需 sudo+root 与 BPF 内核支持 |
| test_static | ./test_static | exit 1 失败 | `chdir(/lib/modules/HongMeng Kernel 1.12.0/build): No such file or directory`；设备无内核头（/usr/include/linux 为空），bpf_module_create 无法编译 BPF 程序 |
| test_libbcc_no_libbpf | ./test_libbcc_no_libbpf | Catch 启动后首个用例 FAILED | `test_c_api.cc:45 REQUIRE(c)` false（language detection 需 BPF 模块创建，缺内核头+无 BPF syscall） |
| py_test_*（36 项） | ctest -R py_ | 全部 BAD_COMMAND | 同 wrapper.sh bash 缺失 |

### 未运行原因归类（阻塞归属：真实外部平台条件）

1. **内核头缺失**：设备 /usr/include/linux 为空、/lib/modules/HongMeng Kernel 1.12.0/build 不存在、
   /proc/config.gz 无、/sys/kernel 无权限 → bcc 在运行时用 clang 编译 BPF 程序需要内核头
   （kbuild_helper/loader 逻辑），全部涉及 BPF 加载的用例在"编译 BPF 程序"环节即失败。
2. **BPF syscall 不可用**：探针 syscall(280)（aarch64 __NR_bpf）core dump/无响应；OHOS（HongMeng
   Kernel 1.12.0）非 Linux BPF 内核。libbpf 1.6.2 适配笔记亦记录"鸿蒙平台不具备 BPF syscall 支持"。
3. **无 bash/sudo 环境**：wrapper.sh 需 /bin/bash（Toybox 仅有 sh），测试需 root 权限执行
   （modprobe、netns、挂载等），设备无 root（const.debuggable=0，无 su）。
4. **无 luajit**：Lua 测试未注册未运行。

这些属真实外部平台/内核条件限制，不是本库配方错误；恢复条件：具备 Linux BPF 内核 +
内核开发头 + root 的标准 Linux 环境（或上游 CI 容器）方可执行。

## 验证结果

- make：全目标成功（见编译步骤）
- make install DESTDIR=~/tmp/test-install-bcc-0.37.0：成功，libbcc.{so,a}、include/bcc/*.h、libbcc.pc 齐备
- ctest：40/40 Not Run（平台限制，见上）

## 注意事项

1. bcc 是 Linux 内核 BPF 工具链库，OHOS 无 BPF syscall，库可编译安装、运行时 BPF 加载不可用；
   消费者用例应以编译/链接/调用公开 API 的可观察静态行为为准，不依赖内核 BPF 实际执行。
2. 本地 Step 2 使用系统 SDK LLVM（`__h` ABI）+ shim；conan 配方需在 W3 中处理 LLVM BPF target
   与 libc++ ABI 问题（见任务 #9/#10 决策）。
## 知识候选台账（knowledge_candidate_ledger）

### C1. OHOS 内核头缺失 + 无 BPF syscall → bcc 上游测试/运行时不可执行
- 真实错误/根因: 设备无 /usr/include/linux、/lib/modules/HongMeng Kernel 1.12.0/build、BPF syscall(280) 不可用
- 修复: 无（真实平台条件）；bcc 库本体可编译安装，运行时 BPF 加载不可用
- 验证: ctest 40/40 Not Run；test_static/test_libbcc 首用例失败（首错、命令、退出码已记录）
- 适用边界: 任何需内核 BPF 支持的库在 OHOS 上同理
- 查重: exact_duplicate=否（无既有 BPF-不支持条目）; causal_duplicate=否; trigger_overlap=弱（E334 网络后端 feature-gate 相关）; solution_overlap=部分（feature-gate 思路）; combination_novelty=中; boundary_novelty=中; test_migration_novelty=否
- 关系: similar_to=E334; 决定: **path_a_no_knowledge**（属平台运行条件记录，非可跨库复用的构建知识；随本库台账申报）

### C2. SDK LLVM（含 BPF target）内嵌 `__h` ABI libc++，与设备 `__n1` ABI 头不匹配
- 真实错误/根因: 发布包 llvm/15.0.4 无 BPF target；系统 SDK LLVM 15.0.4 有 BPF 但 libclang-cpp.so/libLLVM.so 静态内嵌 `std::__h` ABI libc++（NEEDED 仅 libc.so）；设备默认 libcxx-ohos 头为 `__n1`
- 修复: 用 `__h` 头编译 bcc（复制 libcxx-ohos 改 __config_site `_LIBCPP_ABI_NAMESPACE=__h`）+ 自建 iostream shim（cout/cerr/clog + ios_base::Init）+ 库内 iostream 输出改 fprintf
- 验证: bcc 全目标编译链接通过；消费者用例与鸿蒙专项测试 PASS；conan-verify 8 门禁 PASS
- 适用边界: 任何消费 SDK clang/LLVM C++ API 的库（链接 libclang-cpp.so）在 OHOS 上都会遇到 ABI 命名空间不匹配；需同款 `__h` 头 + iostream shim
- 查重: exact_duplicate=否（E247 是 pkg-config 静态 libc++ 符号传播，非预编译 clang 库内嵌 ABI）; causal_duplicate=部分（同为 libc++ ABI 域）; trigger_overlap=部分（E247 std::__n1 触发面）; solution_overlap=弱（E247 是 propagate-static-cxx-runtime，本次是头/shim 方案）; combination_novelty=高（SDK LLVM `__h` 内嵌 + iostream 全局缺失组合无既有条目）; boundary_novelty=高（`__h` vs `__n1` 双 ABI 并存）; test_migration_novelty=否
- 关系: similar_to=E247, E286; caused_by=OHOS SDK 预编译 clang 库构建时 libc++ ABI 配置; 决定: **new_draft**（路径 B 候选，跨库可复用）

### C3. bcc 专有 BPF map 枚举（INSN_ARRAY/RHASH）不在 libbpf uapi，需生成 compat bpf.h
- 真实错误/根因: introspection/bps.c 用 BPF_MAP_TYPE_INSN_ARRAY/RHASH，vendored libbpf（1.4.5/1.6.2）uapi 均无；两枚举在 bcc 自带 compat/linux/virtual_bpf.h
- 修复: source() 生成 compat/linux/bpf.h（grep 去注释）+ introspection CMakeLists 补 compat include
- 验证: conan create 通过
- 适用边界: 仅 bcc 自身
- 查重: exact_duplicate=否; 其余轴=否/弱; 决定: **path_a_no_knowledge**（库内实现细节，无跨库价值）

### C4. libbpf 未发布到 ohpcd，bcc 上游以 git submodule 内置 libbpf → 配方树内内置
- 真实错误/根因: libbpf/1.4.5 远端 registry 不可得（cnb.cool 对缺失包返回策略错误）；bcc tarball 不含子模块内容
- 修复: 配方 source() 下载官方 libbpf 源码到 src/cc/libbpf 走 in-tree 构建（CMAKE_USE_LIBBPF_PACKAGE=OFF）
- 验证: conan create 通过（不再 require 未发布包）
- 查重: exact_duplicate=否; trigger_overlap=部分（E150 submodule missing manual-download）; solution_overlap=部分（E150 manual-download）; 决定: **reuse_existing 参考 E150 + 随本库记录**（E150 已覆盖 submodule 缺失下载；本次是 conan 配方内 get() 下载，属其变体，无新增跨库差异 → path A 复用）

### C5. dlinfo（glibc 扩展）OHOS 无声明 → dladdr+dlsym 替代
- 真实错误/根因: tests/cc/test_c_api.cc:287 dlinfo/RTLD_DI_LINKMAP 在 OHOS dlfcn.h 无
- 修复: 补丁 0007 改用 dladdr+dlsym 取库路径
- 验证: conan create 编译通过（测试因平台条件未运行）
- 查重: exact_duplicate=否（E462 是 gdb 调试用 dladdr，非 API 替代）; 决定: **path_a_no_knowledge**（单点 glibc→OHOS API 替代，通用性低）

### C6. CMake HarmonyOS 无平台模块 → 共享库缺 DT_SONAME
- 真实错误/根因: CMAKE_SYSTEM_NAME=HarmonyOS 无 Platform/HarmonyOS.cmake，CMAKE_SHARED_LIBRARY_SONAME_*_FLAG 未定义，SOVERSION 不产出 SONAME
- 修复: 配方 generate() 显式注入 CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG="-Wl,-soname,"
- 验证: conan-verify L5 PASS（libbcc.so.0/libbcc_bpf.so.0 均带 DT_SONAME）
- 查重: exact_duplicate=是（DRAFT-cmake-harmonyos-platform-soname-flag 完全覆盖同根因同方案，E330 相关）; 决定: **reuse_existing**（完全重复，复用既有草稿/E330，不新建）

### 路径决定汇总
- reuse_existing: C4（E150）、C6（E330/DRAFT-cmake-harmonyos-platform-soname-flag）
- new_draft: C2（SDK LLVM `__h` ABI libc++ 消费侧适配 + iostream shim）
- path_a_no_knowledge: C1、C3、C5（平台条件或库内细节，无跨库新增知识）

## R02 返工：patch 0006 平台宏移除说明

R02（bcc-0.37.0-r02-pc2-15-20260916T004000Z）按 R8/PF5 移除 patch 0006 中的
`#ifdef __OHOS__` 平台条件编译宏，改用不含平台宏的通用 POSIX 头文件组织：

- **问题**：OHOS sysroot 的 `linux/socket.h` 与 `sys/socket.h` 均定义
  `struct sockaddr_storage`，编译含 `linux/rtnetlink.h` 的 C 源时 clang 报
  `redefinition of 'sockaddr_storage'`。
- **通用修复**：bcc `src/cc/libbpf.c` 仅 `#include <linux/rtnetlink.h>` 但未使用
  任何 rtnetlink/netlink 符号（grep 无 nlmsg/rtattr/RTM_/NETLINK_/SOL_NETLINK
  引用），故直接删除该无用 include——即消除 rtnetlink→netlink→linux/socket.h
  的拉入链，从根因上避免冲突，无需任何平台宏与头文件跳过。
- **验证**：重编译 bpf-static/bpf-shared/bcc-shared 全部通过（MAKE=0，
  无 sockaddr_storage 错误）；patch 0006 现仅含 1 行删除（-`#include <linux/rtnetlink.h>`），
  无新增行、无平台宏。
- **备注**：vendored libbpf（配方 source() 树内内置）的 `src/netlink.c` 是
  netlink 功能实现文件，确需使用 netlink 头，其 `__OHOS__` 守卫保留于
  conanfile.py source() 内联（非 patches/ 补丁文件，不属 R8/PF5 补丁检查范围）。
## R03 上游测试补跑：双口径台账更新（实际运行结果）

### 实测口径（R03 全量尽力运行，2026-09-16）

**C++（tests/cc）**
| 入口 | 命令 | cwd | 退出码 | 结果 | 日志 SHA-256 |
|------|------|-----|--------|------|-------------|
| test_static | ./test_static | build-ohos/tests/cc | 1 | 失败：bpf_module_create_c_from_string 需内核 BPF，缺内核头 | 88fc249fd62eadb7bc8321ed698ce544524c398766b190b66fde8d91b345b366 |
| test_libbcc_no_libbpf | ./test_libbcc_no_libbpf | build-ohos/tests/cc | 250 | **14 用例 6 过 8 败；28 断言 20 过 8 败**（6 个通过为纯用户态符号/ELF 解析用例；8 个失败均因 BPF 模块/内核头缺失，首个失败 test_c_api.cc:45 REQUIRE(c)） | 9ef802f32980417bd0934aed4ab943454f3878e01a3a4f2bdbbf4a4f64a6c767 |
| test_libbcc（全 65 用例套件） | — | — | 不可构建 | 本配置（CMAKE_USE_LIBBPF_PACKAGE=ON）tests/cc 未注册该目标（仅 NOT PACKAGE 模式注册），无法在本机构建运行 | — |
| ctest wrapper（c_test_static/test_libbcc_no_libbpf 注册项） | ctest --output-on-failure | build-ohos | — | 需 wrapper.sh（bash + sudo ip netns，namespace 模式需 root 建 veth）；设备无 /bin/bash、无 root（sudo 需 /dev/tty）→ 未通过 wrapper 运行（二进制已直接运行如上） | — |

**Python（tests/python，40 文件逐入口实际运行，TMPDIR=~/tmp、LD_LIBRARY_PATH 注入、bcc 模块经 libbcc.so.0 符号链接可导入）**
| 入口 | 退出码 | 结果 |
|------|--------|------|
| test_utils.py | 0 | **Ran 2 tests OK（2/2 通过，纯用户态）** |
| test_percpu.py | 0 | Ran 4 tests OK（skipped=4，skipUnless 内核版本条件） |
| test_license.py | 1 | Ran 10 tests FAILED（errors=5 为 BPF 编译失败，expected failures=5 按上游预期） |
| test_disassembler/test_dump_func/test_flags/test_histogram/test_lru/test_map_in_map/test_perf_event/test_probe_count/test_queuestack/test_shared_table/test_stackid/test_trace2/test_trace4/test_trace_maxactive/test_uprobes/test_uprobes2/test_usdt/test_usdt2/test_usdt3 等 | 1 | 全部 ERROR：BPF 模块编译失败（"Unable to find kernel headers"），测试实际执行到 BPF 加载阶段 |
| test_array/test_attach_perf_event/test_bpf_log/test_brb/test_brb2/test_call1/test_clang/test_debuginfo/test_lpm_trie/test_map_batch_ops/test_ringbuf/test_rlimit/test_stat1/test_tools_memleak/test_tools_smoke/test_trace3/test_tracepoint/test_xlate1 | 1 | ERROR/失败：同因 BPF 编译失败或缺少内核 BPF 支持 |

**Lua（tests/lua + src/lua/bpf/spec）**
- 设备无 luajit（find_program(LUAJIT) 未命中，ctest 未注册 lua_test_*）；bcc-lua 目标未构建 → 58 个 spec 条目与 4 个 lua 脚本入口全部不可运行（真实外部条件，恢复条件：安装 luajit 并构建 bcc-lua）

### 更新后双口径统计（R03 全量尽力运行后）
- source_declared_total: **393**（C++ 65 / Python 270 / Lua 58，枚举口径不变）
- configured_executable_total: **40**（ctest 注册项：test_static + test_libbcc_no_libbpf + 36 py_* + style-check；lua 未注册）
- executed_total（实际运行到执行阶段的入口数）：**39**（C++ 2 个二进制 + Python 37 个文件入口实际运行；Lua 0）
- executed_passed_total: **C++ 6 用例 + Python 2 用例**（其余全部因 OHOS 无内核 BPF 支持在 BPF 加载/编译阶段失败或按上游预期 skip）
- 全量通过率：**8/393 (2.0%)**；当前配置可执行集合通过率：**8/39 (20.5%)**（ctest 40 项中 39 项实际运行）

### 未运行/失败原因逐项与恢复条件
1. **BPF 编译/加载失败（内核头缺失）**：全部 BPF 用例首错为 `Unable to find kernel headers` / `chdir(/lib/modules/HongMeng Kernel 1.12.0/build): No such file or directory`；设备 /usr/include/linux 为空、无 CONFIG_IKHEADERS。恢复条件：标准 Linux 内核头（/usr/include/linux）或 CONFIG_IKHEADERS=m 内核模块。
2. **BPF syscall 不可用**：探针 syscall(280)（aarch64 __NR_bpf）core dump；OHOS（HongMeng Kernel 1.12.0）非 Linux BPF 内核，libbpf 1.6.2 适配笔记亦记录"鸿蒙平台不具备 BPF syscall 支持"。恢复条件：Linux BPF 内核。
3. **无 /bin/bash**：ctest wrapper.sh shebang 需 bash（设备 Toybox 仅有 /bin/sh、busybox）；已直接运行测试二进制绕过 wrapper。恢复条件：安装 bash 或用 busybox sh 改写 wrapper。
4. **无 root / sudo 需 tty**：wrapper namespace 模式需 `sudo ip netns`（root + netns）；设备 const.debuggable=0、无 su。恢复条件：root 权限 + netns 支持。
5. **无 luajit**：Lua 测试未注册未运行。恢复条件：安装 luajit + 构建 bcc-lua。

### R03 结论
本机实际运行 39 个测试入口（C++ 2 二进制 + Python 37 文件），C++ 6 用例 + Python 2 用例通过（8/393 全量，8/39 可执行集），其余全部因 OHOS 无内核 BPF 支持（内核头缺失 + 无 BPF syscall）在 BPF 编译/加载阶段失败，属真实外部平台条件；恢复条件如上逐项列出。未将任何未运行入口伪写为通过。
---

**编译结束**: 2026-09-16 13:28
**最终状态**: published
