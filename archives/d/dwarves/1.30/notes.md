# dwarves 1.30 编译进度

**日期**: 2026-09-10
**状态**: ✅ 编译中完成

## 步骤记录

| 步骤 | 状态 | 备注 |
|------|------|------|
| Step 0 环境 | ✅ | Python 3.12.9 / Conan 2.29.1 / ohos-aarch64 profile |
| Step 1 依赖 | ✅ | W0: elfutils/zlib/argp-standalone/musl-obstack 均已在 ohpcd 发布 |
| Step 2 源码 | ✅ | 官方 v1.30 tarball SHA-256 核验；libbpf 子模块 @42a6ef6 单独拉取 |
| Step 3 配方 | ✅ | conanfile.py + E091 补丁 + SONAME flag |
| Step 4 构建 | ✅ | conan create 通过（libdwarves*.so + 13 个 CLI） |
| Step 5 上游测试 | ✅ | 全量枚举 6 项，台账 test-ledger.md |
| Step 6 专项测试 | ✅ | 消费者用例 + pahole CLI + 鸿蒙 BTF 解析 |
| Step 7 conan create | ✅ | test_package 全过 |
| Step 8 W3 | ✅ | 本地 CI 模拟通过（L0/L1/L4/L5 全 pass） |

## 发现与知识

- E091：OHOS linux/socket.h 与 musl sys/socket.h 的 sockaddr_storage 重定义（libbpf netlink.c/nlattr.c 需 define-guard）
- 公开头传递：dwarves.h include obstack.h/argp.h/dwarf.h，消费者需显式链接垫片与 elfutils target
- /tmp erofs 只读：上游 pfunct 测试平台阻塞，候选挂载点（HMDFS 2771、/tmpfs、/dev/shm）均不满足 0700
---

**编译结束**: 2026-09-10 21:29
**最终状态**: built
