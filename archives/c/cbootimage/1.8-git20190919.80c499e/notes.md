# cbootimage 1.8-git20190919.80c499e 适配笔记

## 编译环境
- 构建系统: autotools（autoreconf 引导）
- 编译日期: 2026-09-05
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. `init-build` 下载上游 git 快照 tarball（commit 80c499e，2019-09-19）
   URL: https://github.com/NVIDIA/cbootimage/archive/80c499ebbe8a64aa2ee4222e6a8f342f465f6680.tar.gz
   sha256: 7165adf6eb3927cdf8fb295d0b06371bbd600f925536c1ae7498763c9ae864e7
2. 语言预检 lang-preflight: detected=c（与任务 cpp 兼容族，通过）
3. 本地编译: `autoreconf -fi && ./configure --prefix=$DEFAULT_PREFIX && make -j1`
   （上游 tarball 不含 configure，须先 autoreconf 引导）
4. `make install DESTDIR=$TEST_PREFIX` → bin/cbootimage, bin/bct_dump, man pages
5. `make check`: 上游无 TESTS 目标，空操作通过
6. `conan-init` 生成配方 → 修正 conanfile.py（工具型、autoreconf 引导、umask 修复、
   --build/--host triplet、tool_requires automake/libtool）
7. `conan-verify`: G0-G4 + L2/L4/L5 全部 PASS
8. `finish`: W3 本地 CI 模拟 PASS（L0/L1/L4/L5），状态 built

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载 URL 返回 HTML | 传的是项目主页而非 tarball | 用上游 commit tarball URL |
| 2 | autogen.sh aclocal 失败 | 环境 automake 指向 1.17 但只装了 1.16 | 用 automake-1.16/aclocal-1.16 wrapper |
| 3 | configure config.status 报 Permission denied | E114: HMDFS 上 umask 077 生成的 drwx--S--- 临时目录不可写 | 配方 build() 把 configure/config.status 中 umask 077 改为 umask 022 |
| 4 | conan create 报 configure 不存在 | 上游 git 快照不含 configure | 配方 build() 先跑 `autoreconf -fi` |
| 5 | W3 junk_check 命中 9 个其他库基线文件 | 无关历史基线（embree/flatcv 等 tracked 文件） | 按 oh-executor 规则临时 pr.diff 隔离（prdiff 模式）复验后移除 |
| 6 | W3 L1d fake test | test_package test() 用 `|| true` 被判定空壳 | 改为 `cbootimage 2>&1 | grep 'Usage: cbootimage'` 真实断言 |

## 源码修改

无源码补丁（patches/ 为空）。配方层修复见 conanfile.py。

## 依赖版本

- 无第三方依赖（仅 libm log2，系统自带）
- tool_requires: automake/1.18, libtool/2.5.4（registry 已有）

## 验证结果

- `conan create`（干净构建）: PASS
- W3 本地 CI（build_and_test.sh）: PASS（L0/L1/L4/L5；L2 非阻塞警告：工具无 --version/--help）
- test_package: cbootimage usage 输出断言通过

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（autotools，工具型） |
| conandata.yml | 源码 URL + sha256 |
| commands.json | 工具声明（type=tool） |
| test_package/ | 消费者测试（真实执行 cbootimage） |

## 注意事项

- cbootimage 上游无 --version/--help 选项，L2 smoke test 记非阻塞警告。
- 构建命令产物为命令行工具，非库，package_info 无 cpp_info.libs。
---

**编译结束**: 2026-09-05 17:59
**最终状态**: built
