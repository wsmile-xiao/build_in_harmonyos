# libbpf 1.5.1 适配笔记

## 编译环境
- 构建系统: makefile (src/Makefile 自定义)
- 编译日期: 2026-09-19
- 编译器: clang 15.0.4 (OHOS SDK)
- 状态: built

## 上游测试申报表（R51 Step 1 清点）
- 顶层 tests/ 目录：不存在（官方 v1.5.1 tarball 计数 0）
- src/Makefile：无 test/check/selftest/run-tests 目标（grep 计数 0）
- 顶层 Makefile：无测试目标
- CMake/Meson 测试注册：无（全库无 CMakeLists.txt / meson.build）
- 测试源文件（test_*.c / *_test.c / test-*.c）：0 个
- fuzz/bpf-object-fuzzer.c：libFuzzer harness（LLVMFuzzerTestOneInput），非独立用户用例
- ci/vmtest/run_selftests.sh：引用 Linux 内核 tree selftests（test_progs 等），需 BPF syscall +
  内核 VM 环境，OHOS 无 BPF syscall（SIGSYS 拦截），不适用
- **source_declared_total = 0**（官方发布源码无独立上游测试用例），
  configured_executable_total = 0，executed_passed_total = 0，failed = 0，unrun = 0

## 编译步骤
1. init-build libbpf 1.5.1 --url=https://github.com/libbpf/libbpf/archive/refs/tags/v1.5.1.tar.gz
   - tarball sha256: e5ff89750e48ab5ecdfc02a759aa0dacd1e7980e98e16bdb4bfa8ff0b3b4b98f
   - 注意：init-build 嵌套源码检测再次误将 docs/sphinx 提升为源码根（与 1.4.5 同坑），
     已手动重建 .orig/.work 恢复真实 src/include
2. 依赖：libelf（elfutils/0.195 已发布，含全部依赖链 zlib/zstd/musl-fts/musl-obstack）
   - conan install elfutils/0.195 → full_deploy → 私有 prefix /storage/Users/currentUser/tmp/libbpf-deps/prefix
   - zlib/1.3.1.1 从 conan 缓存拷贝头/库进前缀
3. 编译：make BUILD_STATIC_ONLY=y NO_PKG_CONFIG=1 -j2（需注入 CPPFLAGS=-I$PREFIX/include LDFLAGS=-L$PREFIX/lib）
   - 首错：sockaddr_storage 重定义（OHOS SDK linux/socket.h vs sys/socket.h，netlink.c），与历史 1.4.5/1.6.2 相同
   - 修复：netlink.c 顶部平台无关自守卫（先 include sys/socket.h + #if !defined(_UAPI_LINUX_SOCKET_H)
     跳过 linux/socket.h + typedef __kernel_sa_family_t），用 1.4.5 同源补丁
   - 修复后 libbpf.a 构建成功（632KB）
4. staging install：make BUILD_STATIC_ONLY=y NO_PKG_CONFIG=1 DESTDIR=... PREFIX=/usr install
   - install 命令 OHOS 缺失 → /storage/Users/currentUser/tmp/binwrap/install 包装 busybox install
     （/tmp 只读、install 缺失均属已知 OHOS 陷阱）
   - 产物：usr/include/bpf/*.h（13 头文件）+ usr/lib64/libbpf.a + libbpf.pc

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | sockaddr_storage 重定义 | OHOS SDK linux/socket.h 与 sys/socket.h 冲突 | netlink.c 平台无关自守卫（_UAPI_LINUX_SOCKET_H + typedef __kernel_sa_family_t） |
| 2 | install 命令缺失 | toybox 无 install | PATH 注入 busybox install 包装 |
| 3 | init-build 嵌套源码根误判 | docs/sphinx 被提升为源码根 | 手动重建 .orig/.work |
| 4 | W3 JC junk 拦截 | 其他库（cloog）提交前基线脏文件 | 基线隔离复验（详见 reports/baseline-isolation-audit.json） |

## 源码修改

- patches/0001-src-netlink.c.patch：netlink.c 顶部平台无关 sockaddr_storage 自守卫（与 1.4.5 同源）

## 依赖版本

| 依赖 | 版本 | 来源 | 状态 |
|------|------|------|------|
| libelf (elfutils) | 0.195 | conan ohpcd 制品仓 | ✅ 已发布 |
| zlib | 1.3.1.1 | conan ohpcd 制品仓 | ✅ 已发布 |

## 验证结果

- libbpf.a 构建成功 (632KB)
- conan-verify：G1/G2/G3/G4 + L2/L4/L5 全部通过
- conan create test_package：test_libbpf 1/1 Passed（实际调用 libbpf_version_string /
  libbpf_bpf_prog_type_str / libbpf_strerror / btf__new_empty+btf__add_int 等公开 API）
- W3 本地 CI 模拟：L0 pass / L1 pass / L4 pass，pass rate 100% (1/1)
- 消费者用例（consumer_libbpf.c）：CONSUMER_PASS，6 项公开 API 断言全过
  （version=libbpf_version_string() "v1.5" / prog/map/attach 类型字符串 / strerror /
  BTF 类型解析），编译链接运行退出码 0
- 链接命令：-lbpf -lelf -lz -lzstd -lfts -lobstack

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（custom Makefile，静态库） |
| conandata.yml | 官方源码 URL + sha256 + 补丁声明 |
| patches/0001-src-netlink.c.patch | netlink.c sockaddr_storage 自守卫 |
| test_package/ | L1 测试（test.c 调用公开 API + MANIFEST.yml + conanfile.py） |
| manifest.yaml | 版本元数据（built） |
| reports/ | conan-verify 报告 + W3 日志 + 基线隔离审计 |

## 注意事项

1. libbpf 是 Linux 内核 BPF 子系统的用户空间交互库，鸿蒙平台无 BPF syscall
   （seccomp 拦截 SIGSYS），核心 BPF 功能不可用；仅静态库（BUILD_STATIC_ONLY=y）
   可用于 ELF 解析（bpf_object_open）、BTF 处理等非 syscall 功能
2. netlink.c 需平台无关 sockaddr_storage 自守卫编译
3. custom Makefile 依赖的 -I/-L/-l 必须经 CPPFLAGS/LDFLAGS/LIBS 环境变量注入
4. 上游测试：官方 v1.5.1 源码无独立上游测试用例（source_declared_total=0），
   ci/vmtest 需 BPF syscall + 内核 VM，OHOS 不适用

## 知识候选台账（七轴查重）

本适配产生的候选知识与既有知识图谱条目比对结论：

| 轴 | 判定 | 证据 |
|----|------|------|
| exact_duplicate | E119（macro-guard-skip-header）精确覆盖 | netlink.c sockaddr_storage 重定义错误特征与 E119 完全一致（`redefinition of 'struct sockaddr_storage'` + `linux/socket.h` vs `sys/socket.h`），且本任务补丁采用与 E119 相同的方案（`#if !defined(_UAPI_LINUX_SOCKET_H)` + typedef __kernel_sa_family_t 跳过 linux/socket.h） |
| causal_duplicate | E098（cp-chmod-replace）同根因 | `install: command not found`（toybox 无 install）在 E098 中已记录同根因；本任务用 busybox install 包装解决，属同一根因的不同解法 |
| trigger_overlap | 有 | sockaddr 重定义与 install 缺失两个触发均被既有条目 E119/E098 覆盖 |
| solution_overlap | 有 | 本任务解法（平台无关自守卫 + busybox install 包装）分别与 E119/E098 方案同构；1.4.5/1.6.2 历史 notes 已记载同一解法 |
| combination_novelty | 无 | 自定义 Makefile（BUILD_STATIC_ONLY=y NO_PKG_CONFIG=1）+ sockaddr 守卫 + install 包装的组合在 1.4.5/1.6.2 notes 已完整记载 |
| boundary_novelty | 无 | 未发现新适用边界或反例；1.4.5 同版本族（1.4.5/1.6.2）均在同一边界（OHOS 无 BPF syscall，仅 ELF/BTF 可用） |
| test_migration_novelty | 无 | source_declared_total=0，无上游测试可迁移 |

关系字段：
- similar_to: E119, E091（sockaddr_storage 守卫三方案同族）
- caused_by: E098（install 缺失）、OHOS SDK linux/socket.h 与 musl sys/socket.h 不一致（E119/E091 根因）
- prerequisite_of: 无新条目
- conflicts_with: 无

覆盖/新增差异：既有 E119 已完整覆盖 netlink.c 场景（含验证命令），本轮无新增差异；
install 缺失 E098 已覆盖，busybox 包装属实现变体，不构成新知识。

适用边界/反例：libbpf 在 OHOS 仅静态库（BUILD_STATIC_ONLY=y）可用于 ELF 解析/BTF 处理；
BPF 程序加载类 API 因无 BPF syscall（SIGSYS）不可用——该边界 1.6.2/1.4.5 已记载，本轮复现验证无变化。

**决定: reuse_existing（复用 E119/E098，不建新草稿）；path_a_no_knowledge（路径 B 不成立）**——
完整重复且无独立差异，按规则复用原条目；本任务属路径 A 常规基础适配。
---

**编译结束**: 2026-09-19 02:40
**最终状态**: built
