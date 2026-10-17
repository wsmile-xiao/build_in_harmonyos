# pahole 1.31 编译进度（上游项目 acmel/dwarves）

**日期**: 2026-09-26
**状态**: ✅ 完成（built）

## 步骤记录

| 步骤 | 状态 | 备注 |
|------|------|------|
| Step 0 环境 | ✅ | Conan 2.29.1 / ohos-aarch64 profile |
| Step 1 依赖 | ✅ | W0: elfutils/0.195、zlib/1.3.1.1、argp-standalone/1.5.0、musl-obstack/1.2.3 均已在 ohpcd 发布 |
| Step 2 源码 | ✅ | 官方 v1.31 tarball SHA-256 核验（2b651169…）；libbpf 子模块 @374f780 单独拉取（be3ab131…） |
| Step 3 配方 | ✅ | conanfile.py（CMake/C）+ E091 补丁 + CMAKE_INCLUDE_PATH/LIBRARY_PATH 注入 + SONAME flag |
| Step 4 构建 | ✅ | conan create 成功，test_package 3/3 通过 |
| Step 5 上游测试 | ✅ | 上游 6 项全量枚举：1 通过 / 4 skip（缺 vmlinux+perf）/ 1 平台阻塞（/tmp erofs ro） |
| Step 6 专项测试 | ✅ | 消费者用例 + pahole CLI + 鸿蒙 BTF 解析（clang --target=bpf → pahole -F btf）均通过 |
| Step 7 W3 | ✅ | L0/L1/L4/L5 pass，通过率 100%（1/1）；L2 为脚本非阻塞项（详见 reports/test-report.md） |
| Step 8 W4 | ✅ | 审计 verdict=pass，P0/P1 = 0 |

## 发现与知识

- 1.30→1.31 依赖链与 E091 补丁上下文未变：libbpf 子模块 commit 由 42a6ef6 升至 374f780，但
  netlink.c/nlattr.c 的 include 区段一致，1.30 的 0001 补丁对 v1.31 可干净套用（dry-run RC=0）
- E091：非 glibc 的 Linux libc（OHOS musl）下，内核头 linux/socket.h 无条件定义 struct sockaddr_storage，
  与 libc 头 sys/socket.h 冲突（sys/socket.h 的定义在 `#ifndef __MUSL__` 内，但 OHOS clang 未定义 __MUSL__）；
  libbpf netlink.c/nlattr.c 在 include 期间重命名规避，条件用 libc 特性检测
  `#if defined(__linux__) && !defined(__GLIBC__)`（R8：不引入平台宏）
- 公开头传递：dwarves.h include obstack.h/argp.h/dwarf.h，消费者需显式链接垫片与 elfutils target
- /tmp erofs 只读：上游 pfunct 测试平台阻塞，候选挂载点（HMDFS 2771、/tmpfs、/dev/shm）均不满足 0700
- W3 的 L2 冒烟测试未注入 conanrun 运行环境，动态链接的 CLI 无法解析 libdwarves/libdw/libobstack（rc 127）；
  以正确运行环境（test_package 的 env="conanrun"）执行 `pahole --version` 成功，L2 按脚本自身口径记为非阻塞 skip
---

**编译结束**: 2026-09-26 20:59
**最终状态**: published
