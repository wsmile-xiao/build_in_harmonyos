# klibc-run-init 2.0.14 适配笔记

## 编译环境
- 构建系统: makefile（kernel-style kbuild，与父配方 archives/k/klibc/2.0.14 同源同法）
- 适配日期: 2026-09-22
- 编译器: clang 15（aarch64-linux-ohos，hnp 工具链）
- 目标平台: HarmonyOS PC（os=OHOS arch=armv8，KLIBCARCH=arm64）
- 状态: built（首个工程候选通过权威 CI）

## 上游信息
- 名称: klibc-run-init（klibc 源码树 usr/kinit/run-init 子工具配方）
- 版本: 2.0.14（上游 tag 2.0.14，2025-03-04）
- 许可证: run-init 源码 MIT（H. Peter Anvin）；静态链接 klibc libc，包声明沿用
  父配方组合 MIT AND BSD-3-Clause AND GPL-2.0-only，licenses/ 装 usr/klibc/LICENSE
- 官网: https://www.kernel.org/pub/linux/libs/klibc/
- 源码: https://www.kernel.org/pub/linux/libs/klibc/2.0/klibc-2.0.14.tar.xz
- SHA256: 281bfb683e196818412af70b8968b7726475a80ff1c4bd67119e6bf5059f9075（与父配方固定值一致）
- 功能: initramfs 收尾工具——删除 initramfs 内容、把真实根 MS_MOVE 挂回 /、
  chroot 并 exec 指定 init；支持 -d caps 丢弃能力、-c console、-p 保留 initramfs、
  -n dry-run（仅跳过删根/挂载/exec，仍会 chroot）

## 为什么需要独立配方
- 父配方 patch 0004 把 usr/kinit 从 all 目标剔除（libc 本体不含任何工具），
  klibc 包内没有 run-init 可执行文件。
- run-init 是 initramfs 场景的核心工具（switch_root 等价物），OHOS 用户态需要它
  作为独立包交付。
- 先例: archives/k/kbd-vlock/2.8.0（全量上游 tarball 只建子工具）。

## W0 依赖结论

```
依赖数量：0 个 Conan 运行时/库依赖（klibc 源码树自包含，kbuild 纯 C）
构建期依赖：
  - Linux UAPI 头（KLIBCKERNELSRC）—— 同父配方，OHOS sysroot 推导 + 干净头目录
  - 工具链 clang/llvm-ar/llvm-ranlib/llvm-strip/llvm-nm/llvm-objcopy/llvm-objdump/ld.lld
  - perl（syscall 桩/errlist 生成）、GNU make、sh、cp/find
是否需要拆分依赖适配：否
阻塞点：无（父配方已验证全部前置）
```

## 构建步骤（配方 build()）

1. 工具链/sysroot 探测、kernel-headers 干净目录、usr/include 物化 asm/asm-generic/linux
   （全部同父配方）。
2. `make KLIBCARCH=arm64 KLIBCKERNELSRC=... KLIBCASMDIR=... CC=clang ... EXTRA_KLIBCCFLAGS=--target=aarch64-linux-ohos EXTRA_KLIBCLDFLAGS=-m aarch64linux -j1`
   默认目标 all（klcc + klibc）经 patch 0004 递归 scripts/basic + usr/klibc + usr/kinit。
   usr/kinit 闭包连带编译 kinit/ipconfig/nfsmount/fstype/resume（klibc+UAPI 纯 C，可接受）。
3. 断言 usr/kinit/run-init/static/run-init 产出（静态链接 ../lib.a，自包含）。
4. package: 只装 bin/run-init（static 版）与 LICENSE；binary-sign-tool -selfSign 1
   加 .codesign 段（E077）。

## 源码修改（patch）

- 0001/0002/0003 与父配方逐字节相同（usr/include/Kbuild asm 物化与 KLIBCASMDIR、
  signal.h _KERNEL__NSIG 映射、usr/klibc/Kbuild soname cp 替代 ln）。
- 0004-kbuild-libc-kinit-only.patch：父配方 0004 的变体——all 目标保留
  `$(MAKE) $(klibc)=usr/kinit`，仅剔除 usr/dash、usr/utils、usr/gzip。
  已用 git apply 在纯净源码上验证（toybox patch 对该 hunk 形态有解析 quirk，
  与 CI 无关——conan 用自带 PatchSet 解析器应用补丁）。

## 上游测试门禁（NO_UPSTREAM_TESTS，EVIDENCE_COMPLETE）

检查入口与开关（klibc-2.0.14.tar.xz 解包核验）：
1. usr/kinit/run-init/ 目录清单：Kbuild、run-init.c、run-init.h、runinitlib.c——
   无任何测试源文件或测试目标。
2. usr/kinit/run-init/Kbuild：目标仅 static/run-init、shared/run-init、lib-y、install-y，
   无 test/check 入口。
3. usr/kinit/Kbuild：lib-y 与 kinit 可执行目标，无测试入口。
4. 顶层 Makefile：唯一测试目标 `test: klibc` 递归 usr/klibc/tests（第 120-121 行），
   属父配方职责且已在父配方 CI 执行（37/39 passed，2 个失败为上游硬编码与
   OHOS mmap VA 限制，非 klibc 缺陷）。
5. 顶层 Kbuild：subdir- 列表含 usr/kinit 与 usr/klibc/tests，无其他测试入口。
6. 全树检索 usr/kinit 下 test/check 文件名：仅 nfsmount/dummypmap_test.c——
   是 nfsmount 的源码（stub portmap 服务器），不是测试。

结论：run-init 无上游专属可运行测试，记录 NO_UPSTREAM_TESTS。
本包验证以 test_package 负向 smoke 为准（无参调用期望 usage + 退出码 1，
同时验证 E077 签名后 ELF 可被内核 exec）。真实删根/MS_MOVE/chroot 路径需要
root + PID-1 上下文，-n dry-run 仍会执行 chroot（runinitlib.c run_init()），
在 CI/真机均不安全，明确禁止作为门禁。

## 已知边界
- run-init 运行语义（删根/MS_MOVE/chroot/exec init）只能在真实 initramfs 引导
  流程中验证，CI 层面验证止于构建、链接、签名与 usage 路径。
- 静态版 run-init 自包含（klibc lib.a），不依赖 klibc 共享库，可直接放入 initramfs。

## 验证结果（权威 CI）

- 归档：kernel.org 官方 HTTPS 三镜像下载至设备 tmp，SHA256 实测
  281bfb683e196818412af70b8968b7726475a80ff1c4bd67119e6bf5059f9075，与父配方固定值一致。
- 权威入口：ci/conan/build_and_test.sh + ci/conan/profiles/ohos-aarch64，
  CI_PACKAGES=archives/k/klibc-run-init/2.0.14，设备真机执行。
- r1：L0 fail（commands_json_r38）——CLI 工具需软件级 commands.json（R38），补齐后通过。
- r2：conan create 构建与打包通过、test_package ELF/codesign 校验通过，仅 test.sh
  自身 POSIX 语义缺陷（if 条件为假且无 else 时状态码被重置为 0）误报退出码，修复。
- r3（最终，2026-09-22）：Build Summary Success 1 / Failed 0。
  - L0_RESULT=pass（全部结构/质量检查，含 commands.json R38）
  - L1_RESULT=pass（test_package 由 conan create 真实执行；ELF 魔数与 .codesign
    段校验通过；负向 smoke PASS：无参调用 stderr 输出 Usage 且退出码 1）
  - L2_RESULT=skip（run-init 设计上无 --version/--help，非阻塞；与父配方 L2 skip 先例一致）
  - L4_RESULT=pass（patch 静态扫描干净）
  - L5_RESULT=pass（bin/ 含 run-init）
- 日志：run 目录 ci-run-r3.log（权威 CI 全量）、conan-build-r3.log（conan create 增量）、
  ci-run-r1.log/ci-run-r2.log（回修历史）、eng-files-r3.sha256（通过 CI 的工程文件哈希快照）。
