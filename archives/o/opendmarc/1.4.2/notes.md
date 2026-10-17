# opendmarc 1.4.2 适配笔记（OpenDMARC 策略库）

## 编译环境
- 构建系统: autotools（源码包不含 configure，build() 内 autoreconf -fi 引导）
- 编译日期: 2026-08-26
- 目标平台: HarmonyOS PC (arm64, OHOS 6.0, clang 15, libc++)
- 编译器: clang/clang++（OHOS 工具链 /data/service/hnp/bin）
- 状态: built（conan-verify 通过后可标 published）
- Conan: 2.29.1（OHOS 适配版），profile `ci/conan/profiles/ohos-aarch64`

## 依赖
| 依赖 | 版本 | 类型 | 用途 |
|------|------|------|------|
| automake | 1.18 | tool_requires (build) | autoreconf 引导（源码包无 configure） |
| libtool | 2.5.4 | tool_requires (build) | libopendmarc.la 构建 |
| （系统） | libresolv / librt / pthread | system | DNS 解析、定时、线程 |

> 运行时 Conan 依赖：无（库仅依赖 libc/libresolv，已在 OHOS 系统 libc 中）。

## 编译步骤

1. 源码: `https://github.com/TrustedDomainProject/OpenDMARC/archive/refs/tags/rel-opendmarc-1-4-2.tar.gz`
   sha256 `ee1dcdd158fd5fd2b16de2b86980c4a4be60a070641ca19591a713da4e4008bb`
2. 源码包**不携带 configure**（只有 configure.ac + Makefile.am），需 `autoreconf -fi` 引导。
   - conanfile.py 的 build_requirements() 声明 `automake/1.18` + `libtool/2.5.4`
     （均已在 ohpcd 制品仓发布，参考 abiword-plugin-clarisworks 先例）
   - build() 首步 `self.run("autoreconf -fi", cwd=source_folder, env="conanbuild")`
3. configure 参数: `--disable-filter --with-spf --build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos`
   - `--disable-filter`: 跳过 opendmarc milter 过滤程序（需 libmilter，OHOS 无），只构建 libopendmarc 库
   - `--build/--host`: E007 修正，GNU config.guess 不认识 HarmonyOS，无法自行猜测 build type
4. `make -j1`（E074: HMDFS jobserver fifo EPERM，单线程最稳）
5. 上游测试: `make check` → **7/7 PASS**（test_tld / test_finddomain / test_dmarc_parse /
   test_dmarc_fetch / test_xml_parse / test_parse_to_buf / test_alignment，均为本地单元测试，
   带 testfiles/effective_tld_names.dat 数据文件，无网络依赖）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure: cannot guess build type | config.guess 不认识 HarmonyOS（E007） | configure 显式 `--build/--host=aarch64-unknown-linux-ohos` |
| 2 | config.status: ./confXXXXXX/subs1.awk Permission denied | HMDFS 上 umask 077 + mktemp 生成的 0700/setgid 目录不可写（E011/E114） | autoreconf 后 sed 掉 configure 中 `umask 077`（`_drop_umask_077()`） |
| 3 | opendmarc_dns.c: use of undeclared identifier '_res' | OHOS resolv.h（musl 风格）无全局 `_res` 变量 | 补丁 0001：`#else` 分支改用本地 `struct __res_state resp` + `res_init()`/`res_query()` |
| 4 | milter not found | opendmarc 过滤程序依赖 sendmail libmilter，OHOS 无 | `--disable-filter` 只构建库 |
| 5 | conan create: configure: inaccessible or not found | 源码包无 configure，conan 干净解压后直接 configure 失败 | build() 内 autoreconf -fi + tool_requires(automake/libtool) |
| 6 | test_package: dmarc.h not found | 头文件安装在 include/opendmarc/ 子目录 | test.c 用 `#include <opendmarc/dmarc.h>`；conanfile `cpp_info.includedirs` 含 include/opendmarc |
| 7 | test_package: opendmarc_policy_connect_init 返回 NULL | connect_init(NULL,0) 预期返回 NULL（ip_addr 不能为空） | test.c 传入合法 IP "192.0.2.1" |
| 8 | make: jobserver mkfifo: Operation not permitted | HMDFS fifo 限制（E074） | 警告非致命；主包 make 用 -j1 |

## 源码修改

- `libopendmarc/opendmarc_dns.c`: `_res` 全局变量 → 本地 `struct __res_state`（OHOS musl libc 兼容）
- 固化补丁: `patches/0001-libopendmarc-opendmarc_dns.c.patch`（refresh-patch --auto 生成）

## 依赖版本

- automake/1.18（tool_requires，制品仓已发布）
- libtool/2.5.4（tool_requires，制品仓已发布）
- 系统: libresolv、librt、pthread（OHOS libc 自带）

## 验证结果

```bash
# 本地探索编译（工作目录 ~/builds/opendmarc-1.4.2.work）
make check → Testsuite summary: TOTAL: 7  PASS: 7  FAIL: 0

# Conan 配方验证
ohc-run.py conan-verify opendmarc 1.4.2 → G0-G4 + L2/L4/L5 全部 PASS
  - conan create 干净构建成功（含 autoreconf 引导 + 补丁应用）
  - test_package 真实调用 libopendmarc API（DMARC 记录解析 3 断言通过）
```

## 注意事项

- 主产物为库 libopendmarc（.a），同时含 5 个 reports 报告脚本（Perl/sh）→ 已声明软件级 commands.json（R38，binary: false）
- 运行时无 Conan 依赖，纯系统 libc/libresolv
- 平台任务 #323 opendmarc 1.4.2（open，认领中）
---

**编译结束**: 2026-08-26 22:46
**最终状态**: built
