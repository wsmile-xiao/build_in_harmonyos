# kexec-tools 2.0.32 编译进度

**日期**: 2026-09-18
**状态**: ✅ 构建完成

## 步骤记录

| 步骤 | 状态 | 备注 |
|------|------|------|
| Step 1 源码获取 | ✅ | kernel.org 官方 tarball（sha256 41c42765...962087） |
| Step 2 补丁 | ✅ | 4 份补丁（config.guess/config.sub/configure umask/删陈旧 config.h） |
| Step 3 configure | ✅ | 干净 builddir 外部构建，zlib 检测到，lzma/zstd/xen 无头文件自动关闭 |
| Step 4 make | ✅ | kexec + vmcore-dmesg + purgatory + libutil.a 全链构建通过 |
| Step 5 install | ✅ | DESTDIR staging 验证通过（sbin/kexec, sbin/vmcore-dmesg, man8） |
| Step 6 冒烟 | ✅ | kexec --version/--help/无参路径全通 |
| Step 7 上游测试 | ➖ | 上游无 make check；kexec_test 为 x86-only（arm64 不注册），N=0 如实申报 |
| Step 8 深点实测 | ✅ | kexec_load syscall(104) → SIGSYS（OHOS 内核未实现，运行时内核依赖，如实申报） |
| Step 9 conan 配方 | ✅ | conanfile.py + conandata.yml + test_package（实质执行二进制） |
| Step 10 finish/提交 | 🔄 | 进行中 |

## 关键发现（复现要点）

1. **config.guess 老式分支模型**：上游 2020-09-19 版无统一 GUESS 输出机制，
   HarmonyOS 分支必须 `echo ${MACHINE}-unknown-linux-ohos; exit 0`——
   patch-autotools-ohos.pl 生成的 `GUESS=...` 赋值在本版不生效（落到末尾
   "unable to guess system type"）。
2. **config.sub kernel-os 组合列表**：除 ohos-linux 三元组外，还须在末尾
   `case $kernel-$os` 列表行 `linux-gnu* | linux-dietlibc* | linux-android* | ...`
   追加 `| linux-ohos*`，否则 `config.sub aarch64-linux-ohos` 报
   "Kernel 'linux' not known to work with OS 'ohos'"。
3. **HMDFS mktemp setgid 怪癖（新知识）**：`(umask 077 && mktemp -d "./confXXXXXX")`
   创建的目录呈 2700（setgid）状态且拒所有者写入（chmod 显式修正也不生效），
   导致 config.status 创建 subs1.awk 时 Permission denied。绕行：configure 内
   `umask 077 → umask 022`（strace 6.19 配方同款先例）。注意 fallback 路径
   `(umask 077 && mkdir ...)` 创建的 2771 目录可写——问题只在 mktemp -d。
4. **dist tarball 打包瑕疵**：include/config.h（2025-10-16 开发机产物，
   HAVE_LIBZSTD=1）被误打包进 tarball，位于 -I 搜索前端遮蔽 builddir 新
   config.h → zstd.h not found。删除即修复（config.h 是 configure 产物，
   上游 include/Makefile dist 列表误收）。

## 上游测试口径（rule4/如实申报）

- 上游无 make check / ctest / autotests（`make check` → No rule to make target）
- 唯一 test 目标 `kexec_test`（x86 调试 payload）：kexec_test/Makefile 中
  `BUILD_KEXEC_TEST = no`，仅 ARCH=i386/x86_64 时 = yes——arm64 默认形态
  上游即不注册（所有非 x86 平台一致，非 OHOS 专属）
- **N=0**（上游 arm64 注册测试目标数），测试按"工具构建可用性"口径：
  test_package 实质执行 kexec --version/--help/无参 + vmcore-dmesg 错误路径

## 深点实测（W0：kexec_load 在 OHOS 内核形态）

```c
// probe_kexec2.c：syscall(104, 0,0,0,0)
probing kexec_load(104)...
Bad system call (core dumped)   // SIGSYS，退出码 159
```

结论：OHOS 内核未实现 kexec_load/kexec_file_load（syscall 表无此号直接
SIGSYS）。kexec 工具本体构建/链接/选项解析全通；真实加载/热启动动作属
**运行时内核依赖**，按任务口径如实申报（构建可用性验证）。
vmcore-dmesg 为纯文件解析工具，不依赖该 syscall，功能完整可用。
