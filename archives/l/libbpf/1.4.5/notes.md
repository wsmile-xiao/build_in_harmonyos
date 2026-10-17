# libbpf 1.4.5 适配笔记

## 编译环境
- 构建系统: custom Makefile (src/Makefile)
- 编译日期: 2026-09-16
- 编译器: clang 15.0.4 (OHOS SDK)
- 状态: built

## 编译步骤
1. init-build libbpf 1.4.5 --url=https://github.com/libbpf/libbpf/archive/refs/tags/v1.4.5.tar.gz
   - tarball sha256: e225c1fe694b9540271b1f2f15eb882c21c34511ba7b8835b0a13003b3ebde8c（与 .tarball-sha256 一致）
   - 注意：init-build 嵌套源码检测曾误将 docs/sphinx 提升为源码根，已手动重建 .orig/.work 恢复真实 src/include
2. 依赖：libelf（elfutils/0.195 已发布，含全部依赖链 zlib/zstd/bzip2/xz/argp-standalone/musl-fts/musl-obstack）
   - conan install elfutils/0.195 → 私有 prefix /storage/Users/currentUser/tmp/libbpf-deps/prefix
3. 编译：make BUILD_STATIC_ONLY=y NO_PKG_CONFIG=1 -j2（需注入 CPPFLAGS=-I$PREFIX/include LDFLAGS=-L$PREFIX/lib）
   - 首错：sockaddr_storage 重定义（OHOS SDK linux/socket.h vs sys/socket.h，netlink.c），与历史 1.6.2 相同
   - 修复：netlink.c 顶部平台无关自守卫（先 include sys/socket.h + #if !defined(_UAPI_LINUX_SOCKET_H) 跳过 linux/socket.h + typedef __kernel_sa_family_t，与 aircrack-ng 1.7 同构写法）
   - 修复后 libbpf.a 构建成功（610KB）
4. staging install：make BUILD_STATIC_ONLY=y NO_PKG_CONFIG=1 DESTDIR=... PREFIX=/usr install
   - install 命令 OHOS 缺失 → ~/.local/bin/install 包装 busybox install（/tmp 只读、install 缺失均属已知 OHOS 陷阱）
   - 产物：usr/include/bpf/*.h（13 头文件）+ usr/lib64/libbpf.a + libbpf.pc

## 上游测试申报表（R51 Step 1 清点）
- 顶层 tests/ 目录：不存在（tarball 计数 0；GitHub API v1.4.5 根目录确认）
- src/Makefile：无 test/check/selftest 目标
- fuzz/bpf-object-fuzzer.c：libFuzzer harness，非独立用户用例
- ci/vmtest：引用内核 tree selftests（test_progs），需 BPF syscall + 内核 VM，OHOS 不适用
- **source_declared_total = 0**（官方发布源码无独立上游测试用例）

## 已验证能力（参考历史 1.6.2 结论）
- ELF 解析（bpf_object_open）、BTF 处理、错误码转换、版本字符串可用
- BPF syscall 功能（prog load/map create）鸿蒙无 syscall 支持，不可用
---

**编译结束**: 2026-09-16 01:19
**最终状态**: built
