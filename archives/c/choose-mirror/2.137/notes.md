# choose-mirror 2.137 适配笔记

## 编译环境
- 构建系统: 纯 Makefile（单 C 编译单元 choose-mirror.c + mirrors.h，非 cmake/autotools）
- 编译日期: 2026-09-12
- 编译器: clang（OHOS 适配 profile 指定 /data/service/hnp/bin/clang，R33 取自
  tools.build:compiler_executables conf，未用裸 shell 变量）
- 状态: built（conan create rc=0，test_package 实质执行通过）

## 源码与核验
- source_url: https://deb.debian.org/debian/pool/main/c/choose-mirror/choose-mirror_2.137.tar.xz
  （R39 官方源：Debian installer 官方 salsa 仓库 https://salsa.debian.org/installer-team/choose-mirror
  的官方 pool 发布；单 tarball，顶层目录 choose-mirror-2.137）
- tag/version: 2.137（debian/changelog: choose-mirror (2.137) unstable，2026-05-13）
- sha256: 93de4bbb018cd0b011d9b5d914e7bd3bce2f4d67ec0c8591ec4ec6bf0ca53c34
  （174444 字节；.tmp-ci 预下载副本 sha256sum 实测一致）
- 语言: 纯 C（choose-mirror.c 991 行 + mirrors.h）。用户标注 C++ 属 c↔cpp 兼容族
  （R47），按 C 处理，不阻塞。
- license: debian/copyright 原文 "either version 2 ... or (at your option) any
  later version" → GPL-2.0-or-later（任务头标注 GPL-2.0，以 copyright 文件为准取
  -or-later 全称）。

## 上游测试清点（R51 三步法·第一步，如实清点证据）
- tarball 全量文件清单（tar -tJf choose-mirror_2.137.tar.xz）：无任何 tests/ 目录、
  无 test/check 文件（grep -iE "test|check" 对文件清单 = 0 命中，仅 debian/
  choose-mirror-bin.templates* 等模板名含 "test" 字样，非测试）。
- Makefile 全部目标清点：all / choose-mirror / Mirrors.masterlist /
  check-masterlist / debian/iso_3166.tab / debian/*list-countries /
  debian/port_architecture / debian/choose-mirror-bin.templates / mirrors_{http,
  https,ftp}.h / strip / small / ftp / http / https / clean / reallyclean / demo /
  demo.templates —— 无 `check`、`test` 目标。
- 结论：**上游确无测试套件**（0 测试文件 / 0 测试目标）。最接近的可运行验证是
  `demo` 目标（ln -sf + DEBCONF_DEBUG=developer 调 debconf 前端）——OHOS 无
  debconf 前端运行时，不可运行；`demo.templates` 需 po2debconf（gettext 链），
  OHOS 亦无。故 build() 内不运行上游测试（无对象可运行），由 test_package 做
  实质执行测试替代（见下）。

## 适配决策
1. **源码获取**：conan.tools.files.get() 在本环境 PermissionError（libdebian-installer
   notes.md 实测同款）→ conan.tools.files.download() + `tar -xJf --strip-components=1`
   手动解压（source 顶层目录压平到 source_folder 根）。
2. **DEB_HOST_ARCH=arm64 显式传参（不是 aarch64）**：Makefile 第 6 行
   `DEB_HOST_ARCH ?= $(shell dpkg-architecture ...)` 在 OHOS 无 dpkg 无法执行；
   mirrorlist perl 脚本读 $ENV{DEB_HOST_ARCH}（未定义时回退调 dpkg-architecture
   亦失败）→ build() 所有相关命令统一前缀 `DEB_HOST_ARCH=arm64`，CFLAGS 用
   `-DARCH_TEXT='"arm64"'`（单引号壳写法，见踩坑记录）。**Debian 主架构体系里
   aarch64 硬件记为 arm64**，两条实测证据：
   ① Debian stable `Release` 的 `Architectures:` 行 = `all amd64 arm64 armel armhf
   i386 ppc64el riscv64 s390x`——含 arm64、**不含 aarch64**（choose-mirror.c:361
   `strstr(release->archs, ARCH_TEXT)==NULL` 在 aarch64 下会把 Release 判无效）；
   ② choose-mirror.c:899 check_arch() 拼 `.../dists/%s/main/binary-%s/Release`
   ——Debian 目录只有 **binary-arm64**，无 binary-aarch64。
   生成镜像表实测（masterlist 2.137 + 同一 iso_3166.tab，mirrorlist 写
   ./mirrors_http.h）：`DEB_HOST_ARCH=arm64 perl ./mirrorlist http ...` →
   **283 条**（含 `{NULL,NULL,NULL}` 终止行；282 条带 hostname + 1 条
   NULL-country 条目，deb.debian.org + ftp.xx.debian.org 全量）；
   `DEB_HOST_ARCH=aarch64 ...` → **0 条**（仅 NULL 哨兵——masterlist 的
   Ports-architecture 只列 alpha/hppa/.../x32，arch 过滤全滤空）。
   mirrorlist 的 `$hostarch` 仅用于 masterlist 的 arch 字段匹配（archive 分支
   判定 + `-architecture` 过滤），与硬件 ABI 无关；Debian arm64 = 本仓库
   ohos-aarch64 目标同 ABI，arm64 是正确选择。
   备注：mirrors_https[] 为空表是上游数据行为——2.137 版 masterlist 协议指令
   仅 `-http:`（331 Archive-http / 94 CDImage-http / 15 Old-http / 5 Ports-http，
   0 条 `-https:`），与架构取值无关。
3. **mirrors_*.h 生成**：用 OHOS 自带 perl（/data/service/hnp/bin/perl，5.42）直接
   执行上游 ./mirrorlist http|https（shebang 是 /usr/bin/perl，OHOS 不存在 →
   绝对路径调用，不改源码）；USE_FTP 保持上游默认关，mirrors_ftp.h 不生成，
   choose-mirror.c 对 WITH_FTP 是 #ifdef 保护（-DWITH_FTP_MANUAL 对齐上游
   Makefile 默认 USE_FTP_MANUAL=1）。
4. **debian/iso_3166.tab 构建数据准备**（非平台宏）：上游 `isoquery -c |
   cut -f 1,4 | sort`；OHOS 无 isoquery（实测 `/system/bin/sh: isoquery:
   inaccessible or not found`）→ 回退下载官方 iso-codes 4.20.1 源码（与主源码
   同一 Debian pool）解析 data/iso_3166-1.json，生成同格式 `XX<TAB>国家名`
   （249 条，实测与先期用 JSON 生成的 tab 逐行 diff 一致）。格式与 isoquery -c
   输出列（alpha_2 + name）一致，对 mirrorlist 的 ${CC}/${UCC}/${CNAME} 展开
   行为等价（本 masterlist 无 ${CC} 条目，iso tab 仅作国家码→名映射表使用）。
5. **静态链接依赖库**（关键决策）：cdebconf/0.283 包内 package_info 无 cpp_info
   → build() 内手动接线 include/ + lib/。该包 lib/ 同时含 libdebconfclient.so 与
   一份 0.128 代 libdebian-installer.so.4（cdebconf 自包含构建产物）；而独立
   libdebian-installer/0.121 包只有 .a（libdebian-installer.a + libsystem.a +
   libdebian-installer-extra.a）。若走 -l 动态链接，链接器会优先选 cdebconf 包的
   .so（含 0.128 符号版本，且运行时需 RUNPATH 指两个包 lib 目录，OHOS 上
   $ORIGIN 机制不稳）→ **显式 .a 路径静态链接**：libdebconfclient.a +
   libdebian-installer.a + libsystem.a（顺序敏感：两 .a 有 22 个同名符号如
   di_system_init，libdebian-installer.a 在前）+ -lm。产物 NEEDED 仅 libc.so，
   自包含可执行（实测 readelf -d 验证）。
6. **打包**：bin/choose-mirror（R7 自签：binary-sign-tool -selfSign 1
   SHA256withECDSA + os.replace + chmod 755，实测包内二进制含 .codesign 段且
   可执行）；Mirrors.masterlist → share/choose-mirror/（运行/审计参考数据）。
7. **package_type=application**；settings 四项齐全（L0p）；commands.json 软件级
   声明（R38/L0k，bindirs 非空判定 CLI）。

## 构建与验证
- conan create archives/c/choose-mirror/2.137 -pr:h=ci/conan/profiles/ohos-aarch64
  -pr:b=同 --build=missing → **rc=0**（arm64 修复后重跑验证通过）。
- 产物：bin/choose-mirror（ELF arm64，静态自包含，已自签）+ share/choose-mirror/
  Mirrors.masterlist。
- **镜像表非空自检（打回项证据）**：conan create 后抽查构建缓存
  `~/.conan2/p/b/choose*/b/mirrors_http.h`：
  `grep -c '^	{' mirrors_http.h` = **283**（其中 282 条带 hostname + 1 条
  `{NULL, NULL, NULL}` 终止行），`grep -c '{NULL, NULL, NULL}'` = 1，
  首条 `{"deb.debian.org", NULL, "/debian/"}`，末条
  `{"mirror.mythic-beasts.com", "GB", "/debian/"}`——deb.debian.org +
  ftp.xx.debian.org 全量在表。交叉复算（source 缓存 Mirrors.masterlist +
  同配方 iso-codes 4.20.1 回退生成的 iso_3166.tab，249 国）：
  `DEB_HOST_ARCH=arm64 /data/service/hnp/bin/perl ./mirrorlist http
  Mirrors.masterlist debian/iso_3166.tab` → 283 行（含终止行）；
  `DEB_HOST_ARCH=aarch64` 同命令 → 仅 `{NULL, NULL, NULL}`（0 条真实条目），
  与主编实测口径一致。mirrors_https[] 仅终止行（2.137 masterlist 无
  `-https:` 指令，上游数据行为，见决策 2 备注）。
- test_package 实质测试（R34）：C harness（test.c）fork+exec 真实执行包内
  bin/choose-mirror -n，断言 6 项：
  1. 二进制存在可读；2. 退出码 = 139（实测固化：无 debconf 前端时状态机走到
  "SET mirror/country" 后在 cdebconf passthrough 前端 SIGSEGV，本地 8/8 次稳定
  139，conan create 内 2/2 次 139）；3. 两次运行退出码一致（防偶发）；
  4-6. 转录含 VERSION 2 / REGISTER mirror/http/mirror mirror/https/mirror /
  GET mirror/protocol / SET mirror/country（真实状态机里程碑，防 stub 打印同款
  文本的假二进制）+ ELF 字节扫描含 debconfclient_new 符号（静态链入证据）。
  实测输出：`PASS: choose-mirror executed, exit=139, state-machine transcript
  verified ..., debconfclient_new symbol present`。
  转录稳定性补充实测：包内二进制直跑 30/30 次（env -i）+ 文件捕获 20/20 次
  均在 `SET mirror/country` 后段错误、末行一致；harness popen 捕获路径下
  SIGSEGV 瞬间 stdout 缓冲丢失可偶发截断末行（本轮 conan create 2 次 +
  harness 手动复跑 3 次共 5 次 harness 级运行中出现 1 次截断 FAIL，其余
  4 次 PASS），退出码不受影响（截断那轮两次运行均 139，一致性断言仍过）
  ——若 CI 偶发因该截断 FAIL，属已知现象，重跑即复绿，不得反向削弱断言。

## 已知限制 / 遗留风险
- **~~空镜像表~~ 已解决（arm64 修复）**：首轮按 aarch64 构建时编译进二进制的
  mirrors_http/https 表为空；根因是 Debian 主架构体系里 aarch64 硬件记为
  arm64（Release Architectures 与 binary-<arch> 路径均无 aarch64），已改
  `DEB_HOST_ARCH=arm64` + `-DARCH_TEXT='"arm64"'` 重建：mirrors_http[] 实测
  **283 行（282 条真实镜像 + NULL 终止行）**，"选国家→选镜像"环节有全量条目
  可选（见决策 2 与"构建与验证"自检段）。遗留：mirrors_https[] 仍仅终止行——
  2.137 版 masterlist 本身无 `-https:` 协议指令（0 条），属上游数据现状，
  后续 masterlist 增补 https 条目后无需改配方即自动带出。
- **无 debconf 前端**：OHOS 无 debconf 数据库/前端栈，choose-mirror 的交互式
  全流程无法真实走完，退出码 139 为无前端环境下的确定性终点（cdebconf
  passthrough 前端对未注册问题的 GET 处理触发段错误——上游行为，非本适配缺陷）。
  断言已固化 139；若未来 OHOS 生态提供 debconf 前端，139 断言需复核。
- cdebconf 包内捆绑的 0.128 代 libdebian-installer.so.4 未使用（本配方全部静态
  链 .a）；若其他下游包动态依赖 cdebconf，需注意其包内该 .so 的符号版本与
  libdebian-installer/0.121 的差异。
- 版本级 manifest.yaml 已补（第二轮打回项 P2-2，格式对齐
  archives/c/clamassassin/1.2.4/manifest.yaml 先例）。

## 踩坑记录（本次新错误模式）
- `-DARCH_TEXT="aarch64"` 经 self.run（/bin/sh -c）传参时引号被 shell 吃掉 →
  宏值变裸标识符 aarch64（`use of undeclared identifier 'aarch64'`）；反斜杠
  转义 `\\\"` 在 conan 命令包装下又变成 `\"` 原样进编译器（`missing
  terminating '"'`）。正确形态：单引号壳保护 `-DARCH_TEXT='"aarch64"'`（OHOS
  /system/bin/sh 实测单引号内双引号原样保留）。已落知识库草稿。
- popen/pclose 返回的是原始 wait 状态（35584 = 139<<8），必须 WIFEXITED/
  WTERMSIG 解码后再与 fork/waitpid 路径的退出码比较（test.c 首次实现踩中，
  同错误类别 1 次修正，未触发 R43）。
- conan 2.29.1 本环境无 conan.tools.files.untar → 一律 self.run("tar ...")。

---

**编译结束**: 2026-09-12
**最终状态**: built
