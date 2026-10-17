# mbw 2.0 适配记录

## 来源

- 上游: https://github.com/raas/mbw , tag `v2.0`
- 源码归档: `https://deb.debian.org/debian/pool/main/m/mbw/mbw_2.0.orig.tar.gz`(GitHub 在当前网络不可达,Debian 官方源镜像提供同名上游 tarball)
- SHA-256: `557f670e13ff663086fe239e4184d8ca6154b004bd5fde2b0a748e5aa543c87f`
- 构建系统: 裸 Makefile(`mbw: mbw.c`),无 configure 步骤;仅依赖 libc
- 上游自动化测试套件: 0(无 TESTS 目标,仅 `mbw -n 1 -a 8` 冒烟实测带宽)

## 依赖

- 无第三方依赖(仅 libc: calloc/memcpy/gettimeofday/getopt/printf)

## OHOS 构建要点

- CC 显式指定为 OHOS clang(`tools.build:compiler_executables` 或 fallback `clang`)
- 远端 worker 无 `/tmp` 且无构建 uid in /etc/passwd,并行 make 会竞争临时文件 → `-j1` 且 TMPDIR/TMP/TEMP 指向 build_folder/tmp
- 工具类包(application)产物安装到 `bin/`;消费者测试直接运行该二进制

## 真机/CI 运行要点

- OHOS 运行 ELF 需先 binary-sign-tool `sign -selfSign 1`,并用 llvm-readelf 校验 `.codesign` section 后替换原文件(与 lerc 消费者同模式)

## 状态

- 2026-08-30: 本地配方完成,静态检查通过,待 CI 构建验证
