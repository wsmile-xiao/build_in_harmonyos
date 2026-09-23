# blogc 0.20.1 适配笔记

## 编译环境
- 构建系统: autotools（0.20.1 release tarball 仅含 autotools 构建；CMake 只在 git 树中）
- 编译日期: 2026-09-05
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang，OHOS aarch64）
- 设备: HarmonyOS PC（SSH 真机），CONAN_HOME=~/tmp/ch/home-blogc
- 状态: built

## 上游与源码
- 上游仓库: https://github.com/blogc/blogc
- 上游版本: 0.20.1（最新 release tag，v0.20.1）
- 源码: https://github.com/blogc/blogc/releases/download/v0.20.1/blogc-0.20.1.tar.gz
- SHA256: 2ebc929d014bae02fe44377a9b3988f7a3b8259ef579e13daf027f52d9aaf319

## 构建配置
- 三元组: --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu
  （tarball 的 build-aux/config.sub 不含 *-linux-ohos 条目，按 authselect/1.7.1
  同款方案用 gnu triplet；实际目标由 clang 保持 OHOS）
- 特性: --enable-make --enable-runserver --disable-rpmbuild --disable-ronn
  --disable-valgrind --enable-static --disable-shared
- 测试依赖: cmocka/2.0.2（test_requires + PkgConfigDeps 供给 PKG_CHECK_MODULES）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 立即失败 "working directory cannot be determined"，日志大量 "job-working-directory: error retrieving current directory: getcwd: cannot access parent directories" | ohos-aarch64 profile 的 buildenv 将 SHELL/CONFIG_SHELL 指向 HNP bash（/data/service/hnp/bin/bash，bash 5.3.0）；该 bash 的 getcwd() 在 HMDFS 全树上失败（shell-init 报 "Not supported"/"Not a socket"），autoconf configure 强依赖 getcwd 且会经 $CONFIG_SHELL 重跑自身 | 配方 generate() 用 `[shell, -c, pwd]` 在构建目录实测探测候选 shell（harmonybrew bash、/bin/sh 合格，HNP bash 被淘汰），把第一个可用者写进 buildenv 的 SHELL/CONFIG_SHELL |
| 2 | tests/blogc-runserver/check_httpd_utils.c 编译失败 unknown type name 'ssize_t' | OHOS musl 不经 stdlib.h 等头间接暴露 ssize_t（glibc 可以）；上游测试文件直接使用 ssize_t 且未包含 sys/types.h | 补丁 0001-add-sys-types-h-for-musl-ssize-t.patch：include 块补一行 #include <sys/types.h>，不改任何测试逻辑 |
| 3 | configure 的 umask 077 临时目录在 HMDFS 下不可写（E011/E114 家族） | config.status 用 `umask 077 && mktemp -d` 创建临时目录，HMDFS setgid+uid 异位组合使目录不可写 | build() 在运行前把 configure 内 "umask 077" 替换为 "umask 022"（仓库既有知识 E011/E114 同款） |
| 4 | /data/storage/el2/base/haps/entry/files 对 SSH 用户（uid 20001006）不可进入（属主 uid 20020084 应用沙箱） | boxes/2.3.1 默认工作区路径属于另一应用沙箱 | 不再固定使用该路径；先就地探测 ./blogc -v，仅当执行失败才迁移到 ~/tmp/blogc-ws/<版本> 并自签名 |

## 关键实测结论（与既有归档认知的差异）
- HMDFS conan 缓存树上（p/b/... 构建树）ELF 实际可执行：未签名直接可跑，
  AC_RUN_IFELSE 探针（-wrap 能力检测）在 aarch64 真机构建（名义交叉、实际
  同架构）下可真实运行 → have_ld_wrap=yes，全部 -wrap 测试注册。
  boxes/2.3.1 notes 中的 "ELF execution is blocked on the HMFS conan build
  tree" 在当前设备/环境不复现；配方保留自适应回退（探测失败→复制工作区+
  binary-sign-tool 自签名）以兼容 worker 环境差异。
- HNP bash getcwd 失败与目录深度/内容无关（~/tmp 浅层同样失败），是 bash
  5.3.0(HNP) 在 HMDFS 上的普遍问题。

## 上游测试（真实执行，数字以 make check Testsuite summary 与包内
## res/upstream_test_result.json 为准）
- 上游静态注册（TESTS 条目）: 27 = 25 个 cmocka 程序 + 2 个端到端脚本
- 上游 cmocka 内部注册用例: 332（静态 333 减上游自行注释停用的 1 个）
- cmocka 内部注册用例: 333（cmocka_unit_test 计数，静态）
- 实际执行/通过: 见下表（make check 汇总）

| 口径 | 数值 |
|------|------|
| 上游静态声明（TESTS 条目） | 27 |
| 上游实际执行（PASS） | 27 |
| 上游失败（FAIL） | 0 |
| 跳过（SKIP） | 0 |
| cmocka 用例实际执行（Running N test(s) 求和） | 332（全 PASSED） |
| test_package 消费者断言 | 4/4 |

- 汇总来源：make check 末行 "All 27 tests passed"、包内
  res/upstream_test_result.json（total=27 passed=27 failed=0 skipped=0）、
  check.log 中 25 个 cmocka 程序的 [ PASSED ] 计数逐项求和 = 332。

- 未注册/未执行部分（如实披露）：tests/blogc-git-receiver/ 套件仅在
  --enable-git-receiver 时注册（上游默认关闭，其脚本另依赖 git/tar 行为）。

## 上游测试修改说明
- 唯一修改：补丁 0001-add-sys-types-h-for-musl-ssize-t.patch
  （tests/blogc-runserver/check_httpd_utils.c 增加 #include <sys/types.h>，
  OHOS musl 下 ssize_t 需显式包含；不改任何断言与测试逻辑）。

## test_package
- test.sh：用打包的 blogc 二进制做真实端到端渲染断言（template+post 渲染、
  输出 grep 断言、blogc-make -v、blogc -v），输出 HMBS_TEST_PACKAGE_RESULT。
- 包内 res/upstream_test_result.json 由 build() 持久化，test_package 读取并
  重发 HMBS_UPSTREAM_TEST_RESULT 标记（防 conan 缓存跳过 build() 时标记丢失）。

## 已知限制
- blogc-runserver 仅构建并安装，其 2 个 -wrap 测试正常注册执行（httpd_utils
  需补丁 0001）；无其他平台功能缺口。
- commands.json（R38）声明 blogc/blogc-make/blogc-runserver 三个 CLI 工具。
---

**编译结束**: 2026-09-06 02:36
**最终状态**: built
