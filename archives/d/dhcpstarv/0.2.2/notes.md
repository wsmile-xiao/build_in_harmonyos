# dhcpstarv 0.2.2 适配笔记

## 编译环境
- 构建系统: autotools（autoreconf + configure + make；源码无 configure 脚本，需 autoreconf）
- 编译日期: 2026-08-04
- 编译器: clang（OHOS aarch64，/data/service/hnp/bin/clang）
- 状态: published

## 编译步骤

1. 源码获取：GitHub sgeto/dhcpstarv master tarball（sha256 fdd6e3a4...f0d701）。
2. 版本确认：Debian 官方 orig tarball 打包版本 0.2.2（上游 SourceForge 发布版）；configure.ac `AC_INIT([dhcpstarv],[0.2.2],...)`。
3. License 核实：COPYING = GPL Version 3（2007-06-29）；src/common.h 头注释 GPLv3+。
4. 依赖检查：无 libpcap 依赖（configure.ac/Makefile.am/src 零 pcap 引用，debian/control Build-Depends 仅 debhelper+dh-autoreconf）；直接使用 PF_PACKET/SOCK_RAW/SOCK_DGRAM raw socket。
5. 构建：autoreconf → configure（--disable-silent-rules）→ make -j1 → make install。
6. conanfile.py：autotools 配方，package_type=application，in-source layout（上游 Makefile.am 用 nostdinc，config.h 与源同目录查找）。
7. conan create 通过（ohos-aarch64 profile）；test_package smoke test（--help 打印版本 0.2.2，退出码 0）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | autoreconf 失败：Can't locate Automake/Config.pm | 本机 automake 1.17 share 目录为空 | PERL5LIB 指向 share/automake-1.16（0001 补丁不涉及，环境级） |
| 2 | config.status `./confXXX/subs1.awk: Permission denied` | HMDFS 上 mktemp -d ./confXXXXXX（umask 077）建目录后写入被拒 | 0001 补丁：改用源码内 .tmp 目录 + 去掉 umask 077（对齐 apcupsd 0004-configure.patch） |
| 3 | `no member named 'dest' in 'struct udphdr'`（src/dhcp.c:110、src/udp.c:131-134） | OHOS musl netinet/udp.h 的 struct udphdr 为 BSD 风格 uh_sport/uh_dport/uh_ulen/uh_sum，glibc 风格 source/dest/len/check 不存在 | 0002/0003 补丁：改用 BSD 风格成员名 |
| 4 | make 找不到 config.h | 上游 Makefile.am nostdinc + out-of-source 构建 | conanfile.py layout 改 in-source（folders.source/build = "."） |
| 5 | .tmp 目录不存在导致 config.status 失败 | 0001 补丁要求 .tmp 预先存在 | build() 内 autoreconf+patch 后先 mkdir -p .tmp 再 configure |

## 源码修改

3 个补丁文件（patches/）：
- 0001-configure-hmdfs-tmpdir.patch：configure 临时目录机制（autoreconf 后应用）。
- 0002-dhcp.c-udphdr.patch：udph->dest → udph->uh_dport。
- 0003-udp.c-udphdr.patch：udp->source/dest/len/check → uh_sport/uh_dport/uh_ulen/uh_sum。

## 依赖版本

无外部依赖（仅 libc）。本机工具链：clang 15（OHOS SDK 26.0.0.18 sysroot）、autoconf/automake、conan 2.29.1。

## 验证结果

```bash
# 上游测试核验：dhcpstarv 源码无 test/、tests/ 目录，Makefile.am 无 check 目标
# → 上游测试用例通过率：0/0（N/A，上游无测试用例）
# test_package smoke test：dhcpstarv --help 打印 "dhcpstarv - DHCP starvation utility 0.2.2" 且退出码 0
# conan create：通过；conan-verify：PASS（G0-G4）；W3 本地 CI：通过（.ci-result.json exit_code=0）
```

## 知识沉淀

- E215-draft-4AA8.kv/.md：OHOS musl struct udphdr 成员名差异（glibc source/dest/len/check → BSD 风格 uh_*），查重无覆盖，路径 B 候选 + HarmonyOS 系统差异专项候选。

## 结束

- 最终状态：published（本地 finish / W3 本地 CI / .ci-result.json 全部通过，等待提交 PR 与平台 AI Review）
---

**编译结束**: 2026-08-15 11:12
**最终状态**: published
