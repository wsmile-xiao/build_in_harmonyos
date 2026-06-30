# libbpf

## 简介

libbpf 是 Linux 内核 BPF（Berkeley Packet Filter）子系统的用户空间交互库，提供加载、管理 BPF 程序的 API，同时也包含 ELF 文件解析功能。

## OHOS 适配

- **BPF syscall 不可用**：鸿蒙内核（HongMeng Kernel）不具备 BPF syscall 支持，libbpf 的核心 BPF 功能（程序加载、map 操作等）无法运行
- **可用功能**：ELF 解析（bpf_object_open）、BTF 处理等非 syscall 依赖的功能仍可正常使用
- **sockaddr_storage 重定义**：OHOS SDK 的 `linux/socket.h` 和 `sys/socket.h` 同时定义了 `sockaddr_storage`，导致 netlink.c 编译冲突，需要 `#ifdef __OHOS__` 守卫修复
- **构建方式**：仅编译为静态库（`BUILD_STATIC_ONLY=y`）

## 排除与替代

- BPF 程序加载功能 → 不可用（无 BPF syscall）
- netlink BPF 控制功能 → 不可用（需 `sockaddr_storage` 守卫编译）

## 依赖

| 依赖 | 版本 | 类型 |
|------|------|------|
| libelf (elfutils) | 0.192 | 编译必需（头文件 + 静态库） |
| zlib | 1.3.1 | 编译必需 |

## 功能验证

**测试结果**: 11 PASS / 1 FAIL(预期) / 4 SKIP — verdict: **partial**

### 可用功能
- ✅ 版本信息: `libbpf_version_string()` 返回 "v1.6"
- ✅ 错误码转换: `libbpf_strerror()` 正常工作
- ✅ BPF 类型字符串: `bpf_prog_type_str()`, `bpf_map_type_str()`, `bpf_attach_type_str()` 正常
- ✅ BTF 处理: `btf__new_empty()`, `btf__add_int()`, `btf__dedup()` 正常
- ✅ ELF 解析基础设施: `bpf_object__open()` 可读取 ELF 文件并正确拒绝非 BPF 格式

### 不可用功能（SKIP）
- ⏭️ BPF syscall: `bpf_prog_load()`, `bpf_map_create()`, `bpf_obj_get()` — 需 BPF syscall 支持（鸿蒙不可用）

### 链接注意事项
- ⚠️ 需要额外链接 `-lintl_glib`（libelf.a 引用 `g_libintl_dgettext` 符号）
- 完整链接命令: `-lbpf -lelf -lintl_glib -lintl -lz -largp -lfts -lobstack`

## 参考

- 官网：https://github.com/libbpf/libbpf
- 源码：https://github.com/libbpf/libbpf/archive/refs/tags/v1.6.2.tar.gz