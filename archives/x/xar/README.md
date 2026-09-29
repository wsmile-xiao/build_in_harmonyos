# xar 1.8.0.498 — HarmonyOS PC 适配说明

## 概况

`xar`（eXtensible ARchiver）是 Apple 开发的可扩展归档器：XML TOC 记录
归档元数据（校验和/权限/扩展属性），文件堆支持 zlib/bzip2 压缩，
macOS pkg/安装包的基础格式。包含 xar CLI 与 libxar 库。

- 上游：apple-oss-distributions/xar tag xar-498（1.8.0.498 = 1.8.0 系列
  修订 498；mackyle/xar 仓库无 1.8.x 版本归档）
- 形态：tarball 内 xar/ 子目录的手写 Makefile.in + 预生成 configure，
  in-source 构建
- 产物：`bin/xar`（静态链 libxar.a，自包含）+ `include/xar` + `lib/libxar.a`
- 依赖：libxml2/2.15.3.1、zlib/1.3.1、bzip2/1.0.8.2、openssl/3.5.8.1
- 许可证：BSD-3-Clause（源码内部版本串 1.8dev，`xar --version` 输出
  "xar 1.8dev"）

## 适配要点

| # | 问题 | 处理 |
|---|------|------|
| 1 | 2005 版 config.guess/sub（E007：不识别 HarmonyOS/aarch64） | configure 对 host 仅做 `*-*-linux*` case 匹配 + 编译期类型探测（AC_CHECK_SIZEOF，无 AC_RUN_IFELSE）→ 传 `--build/--host=x86_64-linux`（2005 config.sub 可 canonicalize，实测）绕开，build==host 原生模式，config.guess 不运行 |
| 2 | Apple OSS 的 openssl 缺口：hash.c 非 Apple 分支无条件 include <openssl/evp.h>，configure.ac 无任何检测 | require openssl/3.5.8.1 + configure 命令行 `LIBS="-lcrypto"`；补丁将 EVP_MD_CTX 栈上声明改为 EVP_MD_CTX_new/free（1.1.0+ 不透明类型） |
| 3 | configure 硬依赖 xml2-config，libxml2 cmake 包不含该脚本 | generate() 写 shim（aspectc/2.5 先例），`--with-xml2-config` 显式指向，路径取自 conan 依赖包 |
| 4 | `make install` 的 ixar 以 RPATH=<LIBDIR> 链共享 libxar | `--disable-shared` 静态链 libxar.a，包内二进制自包含 |
| 5 | CONFIG_SHELL 缺陷（§12.38①）；HMHDFS umask 077；jobserver EPERM | `env -u CONFIG_SHELL SHELL=/bin/sh` + 绝对路径；configure/config.status umask 077→022 替换；`make -j1` |
| 6 | CLI 工具门禁 | 软件级 `commands.json`（R38） |

## 测试

### 上游

无可自动化测试套件：构建体系无 test/check 目标；xar/test/ 为人工驱动
的 Python 脚本（依赖 xsltproc，无断言框架），test_tools/xar.tcl 为
Tcl 交互驱动。原因完整记录在 test_package/MANIFEST.yml。配方 build()
阶段补做真实归档管线自检（创建→解出→逐字节一致）。

### 消费者（test_package/test_xar.sh，6 项断言）

--version / -cf 创建归档 / -tf 成员列表 / -xf 解出逐字节一致 /
--compression=gzip roundtrip / --dump-toc XML TOC（含成员名与 sha1
校验和元素）。全部离线确定性，真实执行包内安装位二进制（R33/R34）。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 1.8.0.498 | prepared | 首次适配，待真机验证（Windows 阶段 2026-09-27 完成） |
