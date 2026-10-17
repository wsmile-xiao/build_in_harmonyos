# uptimed 0.4.6 适配笔记

## 编译环境
- 构建系统: autotools（git-tag 归档无生成式 configure，autogen.sh 引导）
- 编译日期: 2026-09-18
- 编译器: clang 15.0.4（OHOS aarch64，profile `tools.build:compiler_executables`）
- 状态: built
- worktree: `~/qzy/GLM-53-uptimed-0.4.6`（分支 `feat/uptimed-0.4.6`，基线 ff 至 upstream/main 933943b1e4）
- CONAN_HOME: `~/tmp/ch/home-glm53-uptimed`

## W0 / W0b 记录
- W0 preflight：无外部依赖（零 conan requires；tool_requires 仅构建引导：automake/1.18、libtool/2.5.4、pkgconf/3.0.5，均为制品仓已发布包，`conan list -r=ohpcd` 实查）。
- W0b：归档树无 uptimed 历史归档/notes（全新适配）；`lang-preflight` 通过（C，milestone=lang_checked）。
- 上游 URL：https://github.com/rpodgorny/uptimed（tag v0.4.6）
  sha256=48656498ac30c59b902e98dc5e411e97cbb96278a01946bdf0941d8da72b2ae1（本地实算，conandata.yml/manifest/正文同源）。

## 编译步骤
1. `autogen.sh` 引导（libtoolize/aclocal/autoheader/automake/autoconf；autoconf/m4 走 SDK PATH——显式 tool_requires autoconf 会拉 OHOS perl 与 SDK perl 的 XS 冲突，accel-config/termrec 先例）
2. configure：显式 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`（config.guess 不识别 OHOS uname；`*-linux*` 分支定义 PLATFORM_LINUX，是 libuptimed/urec.c 的 /proc/uptime 启动时间读取路径所必需）+ `--disable-shared --enable-static`（musl 忽略 DT_RUNPATH，静态 libuptimed 保证二进制自包含）
3. HMDFS 组合拳（termrec 先例）：build 目录内 mktemp wrapper（umask 022 建临时目录）+ configure 内 `umask 077 → 022` 受控放宽（E011/E114）+ `unset CONFIG_SHELL / SHELL=/bin/sh`（E386）
4. `make -j1` + `make check`（上游无测试，automake check 目标为空跑，R51 如实记录 0 执行）
5. 无 `make install`：纯 Python 拷贝 `bin/uptimed`、`bin/uprecords`（真身取 `src/.libs/`，libtool wrapper 不可入包）、man 页、样例配置、COPYING

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 首次 conan create 消费者测试 3 例失败：`bin/uptimed: error: '.libs/uptimed' does not exist — This script is just a wrapper` | libtool 在构建树留 wrapper 脚本，真身 ELF 在 `src/.libs/`；package() 误拷 wrapper | package() 改从 `src/.libs/` 取真 ELF |
| 2 | configure.ac 无显式 AC_CANONICAL_HOST，`$host` 依赖 libtool 宏拉入的规范化 | 不传 --host 时 $host 为空，`*-linux*` 分支不命中 → PLATFORM_LINUX 未定义 → /proc/uptime 读取路径缺失 | 显式双 gnu 三元组（termrec 同款） |
| 3 | libuptimed 为 lib_LTLIBRARIES，共享链接的二进制在 OHOS 会因 RUNPATH 失效 | musl 忽略 DT_RUNPATH | `--disable-shared --enable-static` 静态链接（预防性） |

## 源码修改

无补丁（patches: {}）。umask 放宽在构建期对生成的 configure 就地 replace，不落补丁文件（termrec 同款 R6-clean 方案，wrapper 仅存在于 build 目录）。

## 依赖版本

- 无 conan 包依赖（零外部依赖）
- 构建工具：automake/1.18、libtool/2.5.4、pkgconf/3.0.5（tool_requires，制品仓已发布）

## 测试账本（五维，R51）

| 维度 | 数值 | 依据 |
|---|---|---|
| N_static 上游静态用例 | 0 | 无 tests/ 目录；Makefile.am 无 check_PROGRAMS/TESTS；configure.ac 无测试框架宏；源码无测试框架字符串（详见 test_package/MANIFEST.yml 审计） |
| N_registered | 0 | 同上 |
| N_executed | 0 | 上游无测试可执行（build() 仍跑空 check 目标证实其形态） |
| 未执行分类 | 0 | 不存在上游用例 |
| N_consumer 消费者测试 | 1 程序（4 用例） | test_uptimed：`uptimed -v` 版本横幅、`uprecords -v` 版本横幅、`uprecords -?` 选项表、`uptimed -Z` 非法选项非静默失败；实测 4/4 PASS（conan-create.log HMBS 标记 passed=true passedCount=4） |

## 路径 B 判断

- 结论：**纯路径 A**，不形成路径 B。
- 理由：本包全部适配技术点（autogen.sh 引导、显式双 gnu 三元组、mktemp wrapper、umask 077→022、E386 shell 路由、.libs 真身拷贝、静态链接自包含）在归档语料均有已发布先例（termrec/0.19、dhcpoptinj/0.5.3、accel-config 等）且知识图谱已覆盖（E011/E114/E386 相关条目），无跨仓库复用的新知识增量；`draft-review` 查重前置判断为"无新增价值"。
- 证据已留痕：本节 + notes 其余小节。

## 验证结果

```bash
python3 scripts/ohc-run.py conan-verify uptimed 0.4.6
# G1 PASS / G0 PASS / G2 conan create PASS / G3 PASS / G4 / L2 / L4 / L5 全绿
# 消费者测试 test_uptimed 4/4 PASS（HMBS_TEST_PACKAGE_RESULT passed=true passedCount=4）
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/uptimed | uptime 记录守护进程（静态 libuptimed） |
| bin/uprecords | 排行榜查询工具 |
| share/man/man8/uptimed.8、share/man/man1/uprecords.1 | 手册页（tarball 预生成） |
| share/doc/uptimed/uptimed.conf-dist | 样例配置 |
| licenses/COPYING | GPL-2.0 |

## 注意事项

- `uptimed -b`（创建 bootid 标记）依赖可写记录存储目录，未纳入自动化消费者断言；版本/用法/失败路径已覆盖，审计意见见 W4。
- OHOS 真机上未签名 ELF 不可直接执行；conan-verify L2 smoke 已按设备签名流程执行通过。
---

**编译结束**: 2026-09-18 03:09
**最终状态**: built
