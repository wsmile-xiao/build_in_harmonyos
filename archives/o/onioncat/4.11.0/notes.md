# onioncat 4.11.0 适配笔记

## 编译环境
- 构建系统: autotools（发布 tarball 不含 configure，configure.ac + Makefile.am，需 autoreconf 引导）
- 编译日期: 2026-09-11
- 目标平台: OpenHarmony / HarmonyOS PC aarch64（真机原生构建，HongMeng Kernel 1.12.0 aarch64）
- 编译器: clang 15.0.4（OHOS NDK，默认 target aarch64-linux-ohos + musl sysroot）
- 构建工具: autoconf 2.72 / automake 1.17（本地探索）；CI 用制品仓 autoconf/2.72 + automake/1.18
- 状态: built（本地探索编译 + 二进制运行验证全通过，待 W3/PR）

## 探索编译记录（本机实测）
```bash
# 1. autogen（上游脚本序列）
autoreconf -f && automake --add-missing --copy && autoreconf -f
# 2. E011 修复：生成 configure 中 umask 077 -> 022（HMDFS setgid 绕行）
sed -i 's/umask 077/umask 022/g' configure
# 3. configure + make
./configure --prefix=<prefix> && make -j1
```
- configure 全部检查通过：linux/if_tun.h、netinet/ip6.h、struct ip6_hdr/iphdr/ip/ifreq、
  getpwnam_r、ether_ntoa_r 等在 OHOS musl sysroot 全部 yes
- src/ 全部 21 个 .c 编译通过（仅 -Wunused 类警告，无 error）
- 链接产物 bin/ocat（133KB ELF dynamic，NEEDED 仅 libc.so）

## 二进制运行验证（本机实测）
| 命令 | 结果 |
|------|------|
| ocat -h | 输出 "onioncat 4.11.0 (c) Bernhard R. Fischer (OnionCat mode)" + 完整 usage，rc=1（预期） |
| ocat -i pg6mm...ggkid.onion（56 字符 v3 域名） | → fd87:d87e:eb43:e663:f3ab:8e5:5663:2903，rc=0 |
| ocat -o fd87:d87e:eb43:e663:f3ab:8e5:5663:2903 | → 4zr7hkyi4vlggkid.onion，rc=0 |
| ocat -i this-is-not-an-onion-name.onion | err "parameter seems not to be valid onion hostname"，rc=1（预期拒绝） |

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status: can't create ./confXXXXXX/subs1.awk: Permission denied | E011：autoconf 以 umask 077 创建临时目录，HMDFS setgid（2771）目录组无写位，进程 UID 映射差异导致 0700 目录不可写 | sed 改生成 configure 中 umask 077 → 022（xz/tar/wget 同类先例）；配方 build() 内同法处理 |
| 2 | 发布 tarball 无 configure | 上游只在 git 里带 autogen.sh，release 包只有 configure.ac/Makefile.am | build() 内按 autogen.sh 序列 autoreconf -f → automake --add-missing --copy → autoreconf -f；tool_requires autoconf/2.72 + automake/1.18（zzuf 0.15 同型先例） |
| 3 | （预期可能）老版 config.guess 不识别 HarmonyOS | E160 系 | 未遇到：automake 1.17/1.18 的新版 config.guess 原生返回 aarch64-unknown-linux-ohos，无需补丁 |
| 4 | 本机 automake cmd-pkgs 包 shebang 指向不存在 perl 路径 | cmd-pkgs 打包时 perl 前缀与部署机不一致 | 仅本机探索问题：用系统 perl 包装执行；CI 走 conan tool_requires 包不受影响 |

## 源码修改
- 无（零源码补丁）。唯一平台适配（umask）作用于 build() 内生成的 configure，属生成文件改写。

## 依赖
- 零外部库依赖：AC_SEARCH_LIBS([bind],[socket]) 与 AC_SEARCH_LIBS([inet_ntop],[nsl]) 在 OHOS musl 上均空解析（libc 内置）；pthread 由 libc 提供（ax_pthread 探测通过，链接 -lpthread 为无害空库指示）
- tool_requires: autoconf/2.72、automake/1.18（制品仓已发布，W0 实测通过）
- 上游测试套件: 无（configure.ac/Makefile.am 无 TESTS/make check 目标，源码树无 tests/ 目录）—— N=0 豁免口径

## conan create 命令
```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```
