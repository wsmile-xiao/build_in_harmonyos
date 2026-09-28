# eventlog a5c19163ba 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-26
- 编译器: clang/clang++（clang 15.0.4）
- 状态: built

## 编译步骤

1. init-build：源码取自 GitHub `balabit/eventlog` commit `a5c19163ba`（上游无正式 tag，
   该 commit 即版本标识）。GitHub 直连超时，经 gh-proxy.com `git clone --depth 1` 取
   到同一 commit 后本地打包校验。
2. lang-preflight：C 语言（autotools），与任务 cpp 属兼容族，通过。
3. 源码引导：上游 git archive 不含生成的 `configure`（configure.in 时代），需
   `autoreconf -fi`（环境补装 automake 1.16.5 + libtool 2.4.7）。
4. configure/make：`./configure --prefix=$DEFAULT_PREFIX`（本地盲试）后在 Conan 配方内
   以 `--build/--host=aarch64-unknown-linux-ohos --enable-static --disable-shared` 重跑；
   `make -j1`（E074）构建 `libevtlog.a`。
5. 上游测试：tests/ 4 个 noinst 程序逐一运行全部通过（4/4）。
6. conan-init → conan-verify（G1/G2/G3/G4/L1/L4/L5 全 PASS）→ finish（W2 结构 +
   R36 依赖 + W3 本地 CI 模拟全通过）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连超时 | 网络不可达 github.com | gh-proxy.com 镜像 git clone；conandata 用官方 commit archive URL（CI 端 E017 自动注入 ghfast.top 镜像 fallback） |
| 2 | 环境缺 automake/aclocal/libtoolize | 最小 OHOS 镜像仅 autoconf | cmd-pkgs 安装 automake 1.16.5 + libtool 2.4.7；shebang 指向补 perl/bash 链接 |
| 3 | configure 缺失（git archive 无生成物） | 上游不提交生成文件 | 配方 build() 先 `autoreconf -fi`；tool_requires automation，CI 侧同法 |
| 4 | config.guess 不识别 HarmonyOS | uname -s=HarmonyOS | generate() 显式 `--build/--host=aarch64-unknown-linux-ohos` |
| 5 | config.status 临时目录 Permission denied | HMDFS 强制 setgid，`umask 077 && mktemp -d` 生成 drwx--S--- 不可写（E114） | build() 中替换该段为无 umask 的 mktemp 直建 |
| 6 | make -jN jobserver fifo EPERM | HMDFS 不支持 fifo（E074） | make 固定 -j1 |
| 7 | conandata 初始 sha256 不匹配 | 本地 git archive 重打包哈希 ≠ GitHub 官方 archive 哈希 | 以官方 archive 实测 SHA-256 为准（ddd8c19c…） |

## 源码修改

无源码补丁。三个 OHOS 适配点（autoreconf 引导、triplet 显式传入、umask 077 移除）
全部在 conanfile.py `build()`/`generate()` 内实现，不留 patches/。

## 依赖版本

- tool_requires（build host）：automake/1.18、libtool/2.5.4（制品仓已发布）
- 第三方运行依赖：无

## 验证结果

```bash
# 上游测试（worktree 内手动运行，4/4 通过）
tests/evtrec tests/evtfmt tests/evtsyslog tests/evtsyslog-macros   # rc=0 全部

# Conan 干净构建 + 消费者测试
conan create archives/e/eventlog/a5c19163ba -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable    # PASS
# test_package: test_eventlog 1/1 Passed

# W3 本地 CI 模拟（finish 内嵌）
ci/conan/setup.sh + ci/conan/build_and_test.sh     # RC=0, 1/1 Success
```

## 注意事项

- 归档目录含 `.ci-result.json`（finish W3 写入，日志 SHA-256 关联 w3-local-ci.log）。
- 匹配知识 E114（HMDFS umask/setgid 临时目录）、E074（make fifo EPERM）、
  E540（runner-path-prepend）等既有条目，均为已知模式应用。
---

**编译结束**: 2026-09-26 23:10
**最终状态**: built
