# libbpf 1.6.2 适配笔记

## 编译环境
- 构建系统: custom Makefile (src/Makefile)
- 编译日期: 2026-06-02
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

1. init-build libbpf 1.6.2 --url=https://github.com/libbpf/libbpf/archive/refs/tags/v1.6.2.tar.gz
2. 首次编译失败：缺少 libelf 依赖
3. 手动编译 elfutils 0.192 提供 libelf：
   - 用 bzip2recover 恢复损坏的 elfutils 源码 tarball
   - 手动编译 lib/ 和 libelf/ 源文件（绕开 autotools 构建系统因 HMDFS 权限问题反复失败的情况）
   - 修改 eu-config.h：将 strong_alias 替换为空宏（clang 不支持 __attribute__((alias))）
   - 创建 libelf_aliases.c：提供废弃函数的 wrapper 实现
   - 安装 libelf.a + 头文件 + pkg-config 到 ~/usr/local
4. 编译 libbpf：`make BUILD_STATIC_ONLY=y NO_PKG_CONFIG=1`
   - 发现 sockaddr_storage 重定义冲突（OHOS SDK 内部 linux/socket.h 与 sys/socket.h）
   - 修复 netlink.c：添加 `#ifdef __OHOS__` 守卫，提前 include sys/socket.h + typedef __kernel_sa_family_t + 跳过 linux/socket.h
5. 成功构建 libbpf.a (651KB)
6. DESTDIR staging 安装 + 本地安装验证通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 缺少 libelf.h/gelf.h | elfutils 未安装 | 手动编译 elfutils 0.192 的 libelf 组件 |
| 2 | elfutils autotools 构建失败 | HMDFS 权限问题导致 config.status 的 mktemp 失败 | 手动编译绕开 autotools |
| 3 | clang 不支持 strong_alias | __attribute__((alias)) GCC 特有 | eu-config.h 替换为空宏 + libelf_aliases.c wrapper |
| 4 | sockaddr_storage 重定义 | OHOS SDK linux/socket.h 与 sys/socket.h 冲突 | netlink.c #ifdef __OHOS__ 守卫 |
| 5 | libelf.a 嵌套 archive | llvm-ar 将 libeu.a 作为嵌套成员打包，ld.lld 不支持 | 重新打包为扁平 archive |
| 6 | g_libintl_dgettext 未定义 | libelf.a 引用 gettext-glib 的 g_libintl_dgettext 符号 | 链接时添加 -lintl_glib |
| 7 | BPF_ATTACH_TYPE_RAW_TRACEPOINT 未定义 | OHOS SDK linux/bpf.h 缺少该枚举值 | 测试程序改用 BPF_CGROUP_INET_SOCK_CREATE |

## 依赖版本

| 依赖 | 版本 | 来源 | 状态 |
|------|------|------|------|
| libelf (elfutils) | 0.192 | 手动编译 | ✅ 已安装 |
| zlib | 1.3.1 | cmd-pkgs 预编译 | ✅ 已安装 |

## 验证结果

- libbpf.a 构建成功 (651KB, 22 个 .o)
- pkg-config --libs libbpf 返回 -lbpf
- pkg-config --libs libelf 返回 -lelf -lz -largp -lintl -lfts -lobstack

## 注意事项

1. libbpf 是 Linux 内核 BPF 子系统的用户空间交互库，鸿蒙平台不具备 BPF syscall 支持
2. 仅编译为静态库 (BUILD_STATIC_ONLY=y)，可用于 ELF 解析等非 BPF 功能
3. netlink.c 需要 __OHOS__ 守卫修复 sockaddr_storage 冲突
4. elfutils 的 autotools 构建系统在 HMDFS 上不稳定，手动编译更可靠

---

**编译结束**: 2026-06-02 18:26
**最终状态**: built