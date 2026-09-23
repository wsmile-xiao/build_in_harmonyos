# exomizer 3.1.2 — OHOS 适配记录

## 来源核验
- 上游: https://bitbucket.org/magli143/exomizer/ (官方仓库, Mercurial)
- 源码包: https://bitbucket.org/magli143/exomizer/get/3.1.2.tar.gz (Homebrew 同源)
- sha256: `01713f2ee39efc86cbe54bb6011613e097efc3bc532cdc640809e7589cd9c043`
  (2026-09-09 实际下载核对一致)
- 版本核验: changelog.txt 记录 3.1.2 (2021); 与 Homebrew/Nix 打包版本一致

## 构建要点
- 纯 ANSI-C (Makefile: -std=c89 -D_XOPEN_SOURCE=600), 无外部库依赖
- 构建产物: src/ 下 exomizer + exobasic 两个可执行文件 (make 默认目标)
- bison/flex: Makefile 存在重生成规则, 但 tarball 自带预生成的
  asm.tab.c / asm.tab.h / lex.yy.c 且时间戳更新, 实际构建不触发
  (与 Homebrew 无 bison/flex 依赖的构建前提一致)
- LDFLAGS=-s 由 clang/lld 接受
- 构建期自举: make 自动构建 exoraw 并运行以生成 sfxdecr.c (真机原生构建无交叉问题)

## 上游测试 (Makefile.test)
- `make -f Makefile.test test` = 16 个 roundtrip 用例:
  raw / rawb / rawr / rawbr / mem / memf / level / levelf 及各自 -E 变体
- 每例: exomizer 压缩 → 解压 → `cmp` 与原始 vec.h 一致
- 全部仅依赖 exomizer 二进制, OHOS 真机可执行

## 消费者测试 (test_package)
- test_exomizer.c: 真实执行安装的 exomizer 二进制,
  raw 压缩 → 解压 → 字节级比对 (R34, 非空壳)

## 上游测试实测 (2026-09-09, WSL x86_64 Ubuntu 主机基线)
- 8/16 PASS: raw/rawb/rawr/rawbr/mem/memf/level/levelf (roundtrip cmp 全一致)
- 8/16 FAIL (rc=2): 全部 -E 变体 (rawbE/rawrE/rawbrE/memE/memfE/levelE/levelfE/rawE)
  - -E 路径(嵌入加密自解压 runner 的多输入编码)在 x86_64 Linux 主机即失败/段错误,
    属上游测试在现代平台的问题,与 OHOS 无关;真机结果以此基线对照记录,不伪造通过率

## 真机验证结果 (2026-09-09, Harmony PC aarch64 原生)
- conan create: PASS (make CC=clang 构建 exomizer+exobasic,含 sfxdecr 自举)
- test_package: PASS (test_exomizer 真实执行 raw 压缩/解压 roundtrip)
- 上游测试(设备端,包内二进制): 8/16 PASS, 8/16 FAIL(rc=2,全部 -E 变体)
  —— 与 x86_64 主机基线完全一致,确认 -E 嵌入加密路径失败属上游测试
  在现代平台(含 glibc 主机)自身问题,非 OHOS 差异
- 真机/主机结果逐项一致,无伪造通过率

## 已知限制
- 面向 8-bit 复古平台的工具, 在 OHOS aarch64 上以原生 CLI 运行
