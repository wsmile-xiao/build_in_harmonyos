# libdxfrw 0.5.12 适配笔记

## 编译环境
- 构建系统: autotools (configure + make, libtool)
- 编译日期: 2026-09-23
- 编译器: clang/clang++ 15.0.4 (aarch64-linux-ohos)
- 状态: built

## 编译步骤

```bash
# 1. 初始化（手动解压官方 tag 归档，因 tarball 内 7 个 automake 辅助脚本为悬空绝对路径符号链接，
#    工具 tarfile filter='data' 拒绝绝对路径链接；GNU tar 解压后替换为真实脚本）
./configure --prefix=$DEFAULT_PREFIX
make -j1
make install DESTDIR=$TEST_PREFIX
make check   # 上游无测试，输出 Nothing to be done
# 2. Conan 配方
ohc-run.py conan-init libdxfrw 0.5.12
ohc-run.py conan-verify libdxfrw 0.5.12   # G0-G4 + L2/L4/L5 全绿
ohc-run.py finish libdxfrw 0.5.12 built
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 官方 v0.5.12 tarball 解压失败（'ar-lib' is a link to an absolute path） | GitHub 归档内 ar-lib/config.guess/config.sub/depcomp/install-sh/ltmain.sh/missing 是指向 `/usr/share/automake-1.12/*` 的绝对路径符号链接，目标在本机/CI 不存在；Python tarfile filter='data' 拒绝绝对路径链接 | 配方 source() 检测悬空链接并用 build-aux/ 随配方导出的真实 automake/libtool 辅助脚本替换（E490 相关） |
| 2 | configure: cannot find install-sh (conan create 干净解压后) | 同上，install-sh 悬空链接不可用 | 同上（build-aux/install-sh 真实文件替换） |
| 3 | config.status: subs1.awk: Permission denied | E011: configure 中 `umask 077 && mktemp -d` 在 HMDFS 上创建的 0700 临时目录对当前进程不可写 | 配方 source() 将 configure 中 umask 077 替换为 umask 022（E011 标准修复） |
| 4 | libtool Version mismatch error (2.6.2 vs LT_INIT 2.4.2) | 替换 ltmain.sh 时用了 2.6.2 版本，与 configure.ac 生成的 LT_INIT 2.4.2 宏不匹配 | 使用官方 libtool 2.4.2 的 ltmain.sh（package_revision=1.3337 与 configure 内嵌 macro_revision 一致） |
| 5 | make: jobserver mkfifo: Operation not permitted | HMDFS 不支持 mkfifo | 使用 `make -j1` 串行构建 |

## 源码修改

无源码 .patch 文件（全部修复由 conanfile.py source() 内嵌处理）：
- source() 悬空符号链接替换 + E011 umask 修复
- conandata.yml: sha256=81a7eccfd41d1587b1c9acc8ddbceab4c4168b1f19a59cd18344067f4189115f
- test_package: 实质 dxfRW 读写回环测试（test.cpp，R34/PF3）

## 依赖版本

无第三方运行时依赖（纯 C++ 库，仅依赖 C++ 标准库/libc++）。

## 验证结果

```bash
conan create archives/l/libdxfrw/0.5.12 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# → G0-G4 + L2/L4/L5 全部 PASS
# test_package: dxfRW write/read round-trip PASS (1/1)
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 2 配方（Autotools，静态库默认） |
| conandata.yml | 官方源 URL + sha256 |
| build-aux/ | 7 个真实 automake/libtool 辅助脚本（替换 tarball 悬空链接） |
| test_package/ | 消费者读写回环测试 + MANIFEST.yml |
| reports/test-report.md | 上游测试清点（无套件）+ 消费者测试报告 |
| reports/conan-verify-report.md | 配方验证报告 |

## 注意事项

- 上游 0.5.12 无自带测试套件（Makefile.am 无 TESTS、无 tests/ 目录），R51 清点证据见 reports/test-report.md。
- configure 生成的 PACKAGE_VERSION 显示 0.5.11（configure.ac 声明 0.5.12 但生成文件陈旧），不影响库功能。
- 无 commands.json（纯库类型，R38 不适用）。
