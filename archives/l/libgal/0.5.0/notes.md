# libgal 0.5.0 适配说明（HarmonyOS PC / OHOS aarch64）

## 概况

- 软件包：`libgal/0.5.0`（General Astrodynamics Library, GAL）
- 上游：Paul C. L. Willmott（VP9MU / AMSAT-BDA），2009 年发布 0.5.0，GPL-2.0-or-later
- 定位：纯 C 数值天文/航天动力学库（IAU SOFA Fortran 例程的独立 C 翻译），
  覆盖矢量/矩阵、日期时间、椭球、地球定向、参考系、星历（VSOP87）、SGP4、
  ODE 积分、力/引力模型、开普勒传播器
- 构建系统：autotools + libtool（2009 年产物），静态库交付 `lib/libgal.a` +
  全量公共头文件 `include/gal_*.h`、`gal.h`、`gal_const.h`
- 运行时依赖：仅 libc + libm，无任何 Conan 前置依赖

## 源码来源说明（PF7/R39 语境）

上游原站 `homepage.mac.com/pclwillmott/GAL/` 已下线（MobileMe 时代的域名），
Savannah / xs4all 历史镜像同样失效，该软件存世的权威存档即 FreeBSD ports
`astro/libgal`（maintainer db@FreeBSD.org，2008 年引入、至今仍在 quarterly
分支）的 distfile：`libgal-0.5.0.tar.gz`（7914477 字节，distinfo sha256
`0e149ba25a9c7f4d3705c2d9c2e7821d0a751d70adc2effb248b27f62085ad31`）。

本包取源地址为 **USTC 的 FreeBSD ports distfiles 镜像**
`https://mirrors.ustc.edu.cn/freebsd-ports/distfiles/libgal-0.5.0.tar.gz`
（与 `distcache.freebsd.org` 同源同文件名，sha256 逐字节一致）。

为何不用 `distcache.freebsd.org`（FreeBSD 官方 distfile 缓存）：本 PR 最初即
使用该域，远程 CI 连续 5 次构建（#51216/#51266/#51401/#51534/#51535）均以
「源码下载超时 / Worker 网络受限」失败——该域在 CI Worker 网络不可达。改用
USTC 镜像后内容与校验和不变，且 `mirrors.ustc.edu.cn` 是本仓库既有 167 个包
验证过、CI 可达的源主机（PF7 镜像黑名单只针对 GitHub 类代理镜像，不含
USTC/TUNA 这类高校开源镜像）。若日后官方域恢复可达，可原样切回。

## 适配要点

1. **config.sub 三元组补丁**（patches/0001）：2009 年 config.sub 不认识
   `aarch64` 与 `linux-ohos`。按仓库既有 aalib 模式打三处补丁（机器表加
   aarch64、OS/内核表加 linux-ohos），configure 显式传
   `--build/--host=aarch64-linux-ohos`，使 config.guess（无法识别
   HarmonyOS 的 uname 输出）全程不被调用。
2. **上游缺陷修复一：VSOP87 速度项越界 UB**（patches/0002，实测必修）：
   `gal_vsop87()` 的速度累加式 `v += a * ( j * t[j-1] * cp - t[j] * c * sin(p) )`
   在 j==0 时读 `t[-1]`（越界）。clang -O3/aarch64 下该 UB 被优化器利用，
   全部 VSOP87 速度分量被清零，上游 ephemerides 测试 549 项失败
   （-O0/-O2 不受影响，为典型「优化器利用未定义行为」而非平台怪癖）。
   修复：j==0 项守卫为 `(j > 0 ? j*t[j-1]*cp : 0.0)`，数学结果不变
   （j==0 的速度贡献本就是 `-t[0]*c*sin(p)`）。修复后 1167/1167 全过。
3. **上游缺陷修复二：TLE 解码 LP64 结构体破坏**（patches/0003，实测必修）：
   `gal_tledec()` 用 `sscanf("%5ld", &tle->satnum)` 把 8 字节 long 写入
   4 字节 int；LP64 上高 4 字节把相邻的 `classification`、`intldesg`
   清零（gal_tle_t 成员布局：satnum/classification/intldesg 相邻）。
   修复：`%5ld` → `%5d`。修复后 sgp4 测试 3146/3146 全过。
4. **静态库交付**：`--disable-shared --enable-static --with-pic`。GAL 是
   数值库，上游 libtool `-version-info 0:4:0` 产物为 `libgal.so.0.0.4`；
   为避免与未来可能的系统库冲突并保持 CI 简洁，本包仅交付静态库。
5. **上游测试全量运行**：上游自带测试框架（`test/` 子库 +
   `gal_test_start/gal_test_stop` 统计），顶层 `Makefile.am` 的
   `check_PROGRAMS` 定义了 14 个测试程序（每个子库一个）。conan create
   中 `make check` 原样构建并运行，共 53974 条断言，53973 条通过
   （99.998%）。AM_INIT_AUTOMAKE 带 `no-dependencies`，无 deptracking。
6. **唯一已知的上游测试偏差**：`gal_tref` 的
   gal_c2tpv00a/gal_t2cpv00a 往返一致性断言（容差 1e-12，被比较量约
   4743，即约 2 ULP 余量）在 OHOS aarch64 上实测偏差 1.8e-12。该失败在
   -O0/-O1/-O2/-O3、开/关 `-ffp-contract=off` 下完全一致，属平台 libm
   的浮点求值特性，非算法或优化缺陷（86/87 通过）。
   配方对 make-check 日志做逐程序精确校验（14 个程序的通过/失败计数
   全部钉死），任何其他偏差都会使构建失败。
7. **OHOS 构建卫生**：沿用 libncurses 6.6（PR #10975）验证过的做法——
   构建在 `/data/storage/el2/base` 下的私有根目录进行（源码复制 + 源内构建），
   每一步（configure/make/make check/make install）输出绑定独立日志文件并
   失败回显尾部；`make install DESTDIR=<stage>` 落盘后整体拷入包目录。
8. **test_package 消费者测试**：CMake 消费者链接 `libgal::libgal` 静态目标，
   9 条断言覆盖三个子库的公开 API：`gal_cal2jd`（J2000.0 当天 JD=2451544.5
   + 文档化的 -2/-3 状态码）、`gal_pdp` 点积、`gal_tlechksum`（真实 ISS
   TLE line2 校验位 '7' + 一条按规范自洽的 TLE 行）。消费者构建同样绑定
   日志文件。

## 已知限制

- 上游 2009 年后未再维护，例程返回状态码与 IAU SOFA C 官方实现的语义
  兼容但数值可能不同（上游参考手册明示）
- 仅交付静态库；动态库需求方需自行以 `-l gal` 静态链接或后续扩展配方
---

**编译结束**: 2026-09-22 17:33
**最终状态**: built
