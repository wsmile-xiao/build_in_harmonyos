# afflib 3.7.22 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-19
- 编译器: clang/clang++
- 状态: published

## 编译步骤

configure --disable-qemu && make -j1 && make install（源码包无预生成 configure，由配方 build() 先 bootstrap.sh 生成并随配方导出 generated/ 预生成文件）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | bootstrap.sh 失败 | aclocal/automake 无版本脚本为 1.17 缺 Automake/Config.pm 模块 | 0001 补丁：改用版本化命令 aclocal-1.16/automake-1.16 |
| 2 | aftest 写 /tmp 失败 | E002：/tmp 只读 | 0002 补丁：临时目录改为 $HOME/tmp |
| 3 | test_recovery.sh 失败（mktemp need XXXXXX / .raw Invalid argument） | mktemp -t recoveryXXXX 模板缺 XXXXXX → 空基名 → 隐藏文件 .raw 被 aff 工具拒绝 | 0003 补丁：mktemp -d -p TMPDIR 完整模板 |
| 4 | test_passphrase.sh 失败（同根因） | mktemp -t blankXXXXX/wordsXXXX 模板缺 XXXXXX | 0004 补丁：mktemp -d -p TMPDIR 完整模板 |
| 5 | test_afsegment.sh 失败（同根因） | mktemp -t blankXXXXX 模板缺 XXXXXX | 0005 补丁：mktemp -d -p TMPDIR 完整模板 |

## 源码修改

补丁（patches/）：
- 0001-bootstrap.sh.patch：版本化 autotools 命令
- 0002-lib-aftest.cpp.patch：aftest 临时目录 → $HOME/tmp
- 0003-tools-test_recovery.sh.patch：test_recovery.sh mktemp → TMPDIR 完整模板
- 0004-tools-test_passphrase.sh.patch：test_passphrase.sh mktemp → TMPDIR 完整模板
- 0005-tools-test_afsegment.sh.patch：test_afsegment.sh mktemp → TMPDIR 完整模板

## 依赖版本

- openssl/3.5.6、expat/2.8.2、zlib/1.3.1（conan 依赖）

## 验证结果

```bash
# 上游 make check（注册 6 个测试，实测 6/6 全部 PASS）
# lib/test-suite.log:  TOTAL 1 / PASS 1（aftest）
# tools/test-suite.log: TOTAL 5 / PASS 5（test_signing / test_recovery / test_passphrase / test_afsegment / test_crypto）
# test_package L1 消费者冒烟：1/1 PASS
```

## 注意事项

- afflib 为 C++ 静态库，consumers 需链接 libc++（package_info system_libs=['c++']）
- 源码经 deb.debian.org 权威镜像获取（GitHub release tag 在本构建网络 404）

---

**编译结束**: 2026-08-19 23:47
**最终状态**: published
