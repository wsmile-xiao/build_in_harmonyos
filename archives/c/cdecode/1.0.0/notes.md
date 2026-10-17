# cdecode 1.0.0 适配记录

## 来源

- 上游: libb64 1.2 (public domain base64 encode/decode C library),cdecode.c/cencode.c 为核心文件
- 源码归档: `https://deb.debian.org/debian/pool/main/libb/libb64/libb64_1.2.orig.tar.gz`(GitHub 在当前网络不可达,Debian 官方源镜像提供)
- SHA-256: `747f942c6ebfc9edb2b1d4a5f45405acf88e027479476a7bcfc2609411d0f49f`
- 构建系统: 裸 Makefile(`src/Makefile`: `libb64.a: cencode.o cdecode.o`),无 configure 步骤;仅依赖 libc
- 上游自动化测试套件: 0(无 TESTS 目标;仅 src 静态库 + base64 CLI 示例)

## 依赖

- 无第三方依赖(仅 libc)

## OHOS 构建要点

- CC 显式指定为 OHOS clang(`tools.build:compiler_executables` 或 fallback `clang`)
- AR 显式指定(llvm-ar/ar),否则 `$(AR) $(ARFLAGS) $@ $^` 归档失败
- 远端 worker 无 `/tmp` 且无构建 uid in /etc/passwd,并行 make 会竞争临时文件 → `-j1` 且 TMPDIR/TMP/TEMP 指向 build_folder/tmp
- 静态库包: 产物 `libb64.a` → lib/,头文件 `include/b64/*.h` → include/b64/;cpp_info.libs = ["b64"]

## 真机/CI 运行要点

- OHOS 运行 probe ELF 需先 binary-sign-tool `sign -selfSign 1`,并用 llvm-readelf 校验 `.codesign` section 后替换原文件(与 mbw/lerc 消费者同模式)

## 状态

- 2026-08-30: 本地配方完成,静态检查通过,待 CI 构建验证
