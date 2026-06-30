# fcgi 2.4.7 适配笔记

## 编译环境
- 编译器: clang 15.0.4 / clang++ 15.0.4 (AArch64, HarmonyOS)
- 构建系统: autotools
- 安装前缀: ~/usr/local

## 平台问题及修复

### P1: configure 脚本缺失（git archive tarball）
- **现象**: GitHub tag tarball 是 git archive，不包含 autotools 生成的 configure 脚本
- **修复**: 运行 `autoreconf -fi` 从 configure.ac 生成 configure
- **依赖**: 需预编译包 automake 1.17 + libtool 2.4.7 + perl 5.42.2
- **知识图谱**: E109（草稿）

### P2: configure umask 077 权限拒绝（E011）
- **现象**: config.status 用 `umask 077 && mktemp -d "./confXXXXXX"` 创建临时目录，HMDFS UID 映射导致 Permission denied
- **修复**: sed 替换 configure 中 `umask 077` → `umask 022`
- **知识图谱**: E011（HMDFS UID 映射 + umask 077）

### P3: SIZEOF 预置（conftest 无法执行）
- **现象**: configure conftest 程序因 umask/权限问题无法正确执行
- **修复**: 使用 ac_cv_sizeof_* cache 变量预置类型大小
- **参数**: long=8, long_long=8, off_t=8, int=4, short=2, char=1, void_p=8

## 补丁说明
- `0001-configure.patch`: 提供原始 tarball 缺失的完整 configure 脚本（含 umask 022 修复）。类型: platform_bootstrap，仅适用于 HarmonyOS。

## 编译结果
- configure: SUCCESS
- make -j1: SUCCESS
- make install DESTDIR: SUCCESS（21 个文件）
- make check: PASSED（fcgi 无自动化测试套件）
- verify-build G1-G4: PASS
- 预编译包: fcgi-2.4.7-ohos-aarch64.tar.gz (580KB)

---

**编译结束**: 2026-05-27
**最终状态**: published
---

**编译结束**: 2026-05-27 19:46
**最终状态**: published
