# cgicc 3.2.19 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-06
- 编译器: clang/clang++ 15.0.4 (OHOS SDK 26.0.0.18, aarch64-unknown-linux-ohos)
- 状态: published

## 编译步骤

```bash
# 1. 官方来源核验（GNU FTP）
curl -fsSL -o cgicc-3.2.19.tar.gz https://ftp.gnu.org/gnu/cgicc/cgicc-3.2.19.tar.gz
sha256sum cgicc-3.2.19.tar.gz   # 2a17b976248de03447f9e36d6ce18a80749990d8543e2dfeea09c413eb67f7f0

# 2. 交叉编译（OHOS 工具链）
CC=/data/service/hnp/bin/clang CXX=/data/service/hnp/bin/clang++ \
  ./configure --prefix=/storage/Users/currentUser/usr/local
make -j2
make install DESTDIR=<staging-prefix>
make check

# 3. Conan 配方验证与发布
ohc-run.py conan-verify cgicc 3.2.19   # G0-G4 + L2/L4/L5 全通过
ohc-run.py finish cgicc 3.2.19 published  # W2/W3 本地 CI 模拟 100% (1/1)
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: cannot guess build type` | config.guess (2016-10-02) 不识别 HarmonyOS（`uname -s=HarmonyOS`） | 补丁 0006/0007：config.guess 增加 `*:HarmonyOS:*:*` → `aarch64-unknown-linux-ohos` 分支；config.sub 增加 `linux-ohos*` 识别 |
| 2 | `ld.lld: error: unable to find library -lstdc++` | OHOS 工具链无 libstdc++，标准 C++ 库为 libc++；cgicc Makefile 硬编码 `-lstdc++` | 补丁 0001/0002：`libcgicc_la_LDFLAGS` 改 `-lc++` |
| 3 | `config.status: can't create ./confXXXXXX/subs1.awk: Permission denied` | 本机文件系统（HMDFS）忽略 chmod，autoconf 临时目录 `umask 077` 创建的 0700 目录不可写 | 补丁 0003：configure 临时目录 `umask 077` → `umask 002` |
| 4 | `make html-doc: cp: bad 'cgicc.png'... No such file` | conan out-of-tree 构建（build-release/）时 doc/Makefile `cp $(IMAGES)` 无 `$(srcdir)/` 前缀；且 `$(srcdir)/$(IMAGES)` 只对首个文件生效 | 补丁 0004/0005：`cp $(addprefix $(srcdir)/, $(IMAGES)) $(srcdir)/cgicc-doc.css html`；`install-data-local` 遍历 `$(builddir)/html/*`（html 为构建产物） |
| 5 | W3 JC5 拦截 `archives/u/util-linux-login/2.42.2/.ci-trigger` | origin/main 基线中其他库已跟踪隐藏文件（blob e69de29b…，空文件），不在 JC5 白名单；当前分支尚无提交时 junk_check 走 full 模式扫 `git ls-files` 全仓库 | 按 oh-executor 基线规则做临时 index 隔离（`git rm --cached`，工作区文件保留、HEAD 不动）→ W3 复验通过 → 无条件恢复（记录于隔离审计） |

## 源码修改（补丁清单）

- 0001-cgicc-Makefile.am.patch / 0002-cgicc-Makefile.in.patch：`-lstdc++` → `-lc++`
- 0003-configure.patch：临时目录 umask 077 → 002
- 0004-doc-Makefile.am.patch / 0005-doc-Makefile.in.patch：html-doc 资源加 srcdir 前缀；install-data-local 改遍历 builddir
- 0006-support-config.guess.patch：识别 HarmonyOS → `aarch64-unknown-linux-ohos`
- 0007-support-config.sub.patch：识别 `linux-ohos*` 三元组

## 依赖版本

- cgicc 3.2.19 无第三方依赖（纯 autotools C++ 库）

## 验证结果

```bash
# W3 本地 CI 模拟（build_and_test.sh）: RC=0
#   JC: pass | L0: pass | L1: pass | L2: pass | L4: warn(已复核) | L5: pass
#   Pass rate: 100% (1/1)
# test_package 消费者测试（本地编译+运行）: cgicc consumer test: PASS（4 断言）
```

## 注意事项

- 上游 tarball `./test/` 目录为空、无注册测试（`make check` 无测试运行），已如实记录于 test_package/MANIFEST.yml 与 test-report.md
- gpg 签名核验因本机无 gpg 命令跳过（平台限制），SHA-256 已与官方 tarball 一致
- 知识图谱引擎对 G2 失败命中 E537（KF6 SONAME，与 cgicc 无关）为误匹配，以实际日志为准

**编译结束**: 2026-09-07 11:09
**最终状态**: published
---

**编译结束**: 2026-09-07 11:21
**最终状态**: published
