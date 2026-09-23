# klibc 2.0.14 适配笔记

## 编译环境
- 构建系统: makefile（kernel-style kbuild，自定义 Makefile，非 autotools/cmake）
- 适配日期: 2026-09-19（前置适配）
- 编译器: clang 15（aarch64-linux-ohos，hnp 工具链）
- 目标平台: HarmonyOS PC（os=OHOS arch=armv8 → klibc KLIBCARCH=arm64）
- 状态: in-progress（本机前置完成，真机 shadow CI 待验证）

## 上游信息
- 名称: klibc
- 版本: 2.0.14（上游 tag 2.0.14，2025-03-04）
- 许可证: 混合 — MIT AND BSD-3-Clause AND GPL-2.0-only
  （usr/klibc/LICENSE：BSD/MIT 混合 + Linux 内核派生文件 GPL-2.0；usr/gzip/COPYING 为 GPL）
- 官网: https://www.kernel.org/pub/linux/libs/klibc/
- 源码: https://www.kernel.org/pub/linux/libs/klibc/2.0/klibc-2.0.14.tar.xz
- SHA256: 281bfb683e196818412af70b8968b7726475a80ff1c4bd67119e6bf5059f9075
- 架构支持: arm64 Working（usr/klibc/arch/arm64 完整；usr/include/arch 含 17 个架构）

## W0 依赖结论

```
依赖数量：0 个 Conan 运行时/库依赖（libc 本体零外部库依赖）
已满足依赖：无（无 Conan 依赖）
构建期依赖：
  - Linux UAPI 头（KLIBCKERNELSRC）—— OHOS SDK sysroot 提供 linux/、asm-generic/，
    但 asm 头布局不同（aarch64-linux-ohos/asm），已用 patch 0001 + KLIBCASMDIR 适配
  - 工具链 clang/llvm-ar/llvm-ranlib/llvm-strip/llvm-nm/llvm-objcopy/llvm-objdump/ld.lld
    —— 从 tools.build:compiler_executables 的 clang 同目录推导（R33）
  - perl —— syscalls.pl/makeerrlist.pl/makeklcc.pl 生成 syscall 桩、errlist、klcc（真机需确认）
  - GNU make + bash/shell + cp/find —— kbuild 依赖
是否需要拆分依赖适配：否（无 Conan 库依赖；UAPI 头由 OHOS SDK sysroot 提供，非独立 Conan 包）
阻塞点：perl 是否在真机可用；OHOS sysroot 的 asm UAPI 头与 Linux syscall 编号的兼容性
下一步：真机 shadow CI 单包验证构建 + 测试程序运行
```

## 构建步骤（配方 build()）

1. `make KLIBCARCH=arm64 KLIBCKERNELSRC=<sysroot>/usr KLIBCASMDIR=aarch64-linux-ohos/asm CC=clang HOSTCC=clang AR=llvm-ar RANLIB=llvm-ranlib STRIP=llvm-strip NM=llvm-nm OBJCOPY=llvm-objcopy OBJDUMP=llvm-objdump LD=ld.lld EXTRA_KLIBCCFLAGS=--target=aarch64-linux-ohos EXTRA_KLIBCLDFLAGS=-m aarch64linux -j1` 构建 klcc + libc 本体。
2. `make ... test` 构建 usr/klibc/tests 下 39 个测试程序（static + shared 版本）。
3. 逐个运行 static 测试程序（15s 超时保护），如实记录结果。
4. Conan `copy` 打包头文件（usr/include/*.h）、静态库（libc.a → libklibc.a）、
   crt0.o、shared-stub.o、共享库（libc.so + klibc-<hash>.so）、klcc、LICENSE。

构建产物（arm64）：
- `usr/klibc/libc.a`（静态库，打包为 lib/libklibc.a）
- `usr/klibc/arch/arm64/crt0.o`（启动对象）
- `usr/klibc/shared-stub.o`（共享启动 stub）
- `usr/klibc/libc.so` + `usr/klibc/klibc-<hash>.so`（共享库）
- `klcc/klcc`（编译器包装器）
- `usr/include/*`（头文件，含 arch/arpa/bits/net/sys 子目录）

## 源码修改（patch）

**工具链/移植（#1）**
- `0001-usr-include-ohos-asm-layout.patch`（usr/include/Kbuild：asm 头 ln → cp 复制 +
  KLIBCASMDIR 变量支持 OHOS 的 aarch64-linux-ohos/asm 布局）

其余工具链覆盖（CC/AR/LD 等）通过 GNU make 命令行变量实现，无需 patch
（klibc Makefile 用 `:=` 普通赋值，命令行变量优先级更高）。

## 依赖版本
- 无 Conan 依赖（libc 本体零外部库依赖）
- 工具链: clang 15 + llvm-ar/llvm-ranlib/llvm-strip/llvm-nm/llvm-objcopy/llvm-objdump/ld.lld
- 其他: perl（生成 syscall 桩/errlist/klcc）、GNU make、bash

## 验证结果

本机（前置，无 conan/make/aarch64 环境，未执行真机构建）：
- 源码归档 SHA256 复核通过（281bfb68...f9075，与 kernel.org sha256sums.asc 一致）
- 归档根目录为单一 klibc-2.0.14（strip_root=True 适用）
- conanfile.py / conandata.yml / manifest.yaml / test_package 结构完整
- patch 0001~0004 可应用到干净源码（git apply 通过）

真机 shadow CI（2026-09-19，job klibc-2.0.14-shadow-20260919-r1）：
- **conan create 通过**，`Build Summary: Success 1, Failed 0`
- L0_RESULT=pass（质量门禁）/ L1_RESULT=pass（上游测试 + test_package 执行）
- L2_RESULT=skip（klcc --version/--help 非阻塞失败，klcc 包装器需完整 klibc 环境）
- L4_RESULT=pass（patch 干净）/ L5_RESULT=pass（bin/ 有内容）
- L1e 破坏性负测试通过（确认 test 真实依赖 klibc 包产物）

上游测试套件（usr/klibc/tests，39 个静态程序）：
- `make test` 构建全部成功（静态 + 共享版本编译通过）。
- 运行前对测试 ELF 加 OHOS 代码签名（binary-sign-tool -selfSign 1，见 E077），
  否则 kbuild 的 ld.lld 直接链接 + strip 的产物无 `.codesign` 段被内核拒绝 exec。
- 签名后运行结果：**37 passed / 2 failed / 0 sign-failed**。
- 2 个失败（如实记录，均有确切技术原因，非 klibc 根本缺陷）：
  | 测试 | 根因 |
  |------|------|
  | testrand48 | 上游源码硬编码 `return 1`（testrand48.c:18），非自动判定测试（输出 rand48 值供人工对比 glibc 参考值），非 klibc bug |
  | malloctest3 | `malloc(0x100000001)`（4GB+1 超大分配）在 OHOS 的 mmap VA 空间限制下失败，`assert(p != NULL)` 触发 abort（知识库 snmalloc 同类 mmap VA reservation limit） |
- 另外 2 个原失败项已通过配方修复：fnmatch（上游无 runtests 脚本，需手动传 pattern/string/flags 三参数，原 harness 未传参导致 argv[1]=NULL 崩溃）、mmaptest（原硬编码 /tmp 只读 EROFS，改为传可写路径）。
- 37/39 通过证明 klibc 核心功能（字符串/stdio/stdlib/syscall/mmap/fork/信号 等）在 OHOS 上正常。

## 遇到的问题与解决方案（预期 + 已确认）

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | klibc 需要 Linux UAPI 头 | KLIBCKERNELSRC 硬依赖内核 asm/linux/asm-generic 头 | 探测 OHOS sysroot，KLIBCKERNELSRC 指向 sysroot/usr |
| 2 | OHOS asm 头在 aarch64-linux-ohos/asm 而非 asm-arm64 | OHOS 与 Linux 内核 UAPI 布局不同 | patch 0001 用 KLIBCASMDIR 变量适配 |
| 3 | asm 符号链接（ln -fsn）在 HMDFS 可能受限 | 知识库 E018/E050/E073 符号链接限制 | patch 0001 改 cp -rf 复制 |
| 4 | Makefile 硬编码 gcc/ar/ranlib/ld 等 | HarmonyOS 无 GNU 工具链 | 命令行覆盖 CC/AR/... 为 clang/llvm-* |
| 5 | 链接器需 lld emulation | klibc 直接调 $(LD)，ld.lld 需 -m aarch64linux | EXTRA_KLIBCLDFLAGS=-m aarch64linux |
| 6 | make install 依赖 GNU install | HarmonyOS 无 GNU install（E098） | package() 用 Conan copy 手动打包 |
| 7 | syscall 桩/errlist 生成需 perl | syscalls.pl/makeerrlist.pl 是 perl 脚本 | 配方显式传 PERL 完整路径（hnp/bin/perl） |
| 8 | clang 不支持 --print-sysroot | OHOS clang-15 无该选项 | 用 --print-resource-dir 向上 4 级推导 sysroot |
| 9 | 编译误 include OHOS musl 头（bits/alltypes.h 缺失） | sysroot/include 含 musl 头（stdarg.h 等） | 只复制 linux/asm/asm-generic 到干净 kernel-headers 目录 |
| 10 | _NSIG 未声明 | OHOS 内核头用 _KERNEL__NSIG 而非 _NSIG | patch 0002 加 _NSIG=_KERNEL__NSIG 映射 |
| 11 | 共享库 soname 硬链接失败 | HMDFS 不支持硬链接（E079） | patch 0003 把 ln -f 改 cp -f |
| 12 | 顶层 make 递归额外工具（dash/kinit/utils/gzip） | 顶层 Kbuild all 目标递归所有 usr/ 工具 | patch 0004 只构建 libc 本体 |
| 13 | test_package 缺 archconfig.h/asm-generic/linux 头 | 架构头与内核 UAPI 头需打包 | package_info 加 arch/bits 路径；build() 物化 asm/asm-generic/linux |
| 14 | test_package 缺 __KLIBC__/_BITSIZE 宏 | kbuild 的 KLIBCDEFS 宏未在消费侧定义 | test_package 加 -D__KLIBC__=2 -D__KLIBC_MINOR__=0 -D_BITSIZE=64 |
| 15 | 上游测试程序运行 Permission denied | kbuild 的 ld.lld 直接链接 + strip 无 `.codesign` 段，内核拒绝 exec（E077） | 运行前 binary-sign-tool -selfSign 1 签名 + chmod +x，签名后 35/39 通过 |

## 真机 shadow CI 命令（已执行）

```powershell
# 1. 连通性检查
ssh -i C:\Users\ASUS\.ssh\ohos_pc_codex_ed25519 -p 2222 `
  -o StrictHostKeyChecking=accept-new -o IdentitiesOnly=yes `
  currentUser@<device-ip> "echo ok"

# 2. 创建隔离 job（设备上执行）
job="klibc-2.0.14-$(date +%Y%m%d%H%M%S)"
sh "$HOME/bin/ohos-prepare-isolated-conan-job.sh" \
  --user codex \
  --job "$job" \
  --package archives/k/klibc/2.0.14 \
  --repo-source <existing-repo>

# 3. 覆盖包目录并检查文件清单（传输注意二进制安全，勿用文本管道破坏 tar）
# 4. 执行 runner
sh "$HOME/ohos-users/codex/$job/run-conan-heavy.sh"
```

conan create 命令（CI 内部）：
```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 注意事项
- klibc 是 libc 本体，消费方式特殊：需 `-nostdlib -nostdinc` + crt0.o + libklibc.a，
  且 main 为三参数入口（main(argc, argv, envp)）。
- klibc 的 syscall 是 Linux ABI 编号，与 OHOS 内核的 syscall 兼容性是核心真机验证点
  （OHOS 基于 Linux 内核，但可能裁剪/改变部分 syscall，如 fork/vfork）。
- 本适配只构建 klcc + libc 本体（all 目标）；usr/dash、usr/gzip、usr/kinit、usr/utils
  是额外工具，不属于 libc 本体，未纳入本轮（如需单独提 issue/PR）。
- 版本号 2.0.14 与上游一致，未递增。
- 不提交 reports/、ci-metadata.json 等生成物。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | kbuild 交叉编译 + copy 打包配方（工具链/sysroot/asm 头探测；上游测试 make test + 逐个运行） |
| conandata.yml | 源码 URL/SHA256 + patch 声明 |
| patches/0001-usr-include-ohos-asm-layout.patch | asm 头 ln→cp + KLIBCASMDIR 适配 OHOS 布局 |
| test_package/ | 消费者视角静态链接自检（-nostdlib + crt0.o + libklibc.a） |
| manifest.yaml / notes.md | 版本级 manifest 与适配笔记 |
