# libdvbcsa 1.1.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-02
- 编译器: clang/clang++
- 状态: published

## 编译步骤
```bash
./configure --prefix=$DEFAULT_PREFIX
make -j1
make install DESTDIR=$TEST_PREFIX
```
无特殊配置选项， 标准autotools 三步编译。
## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 不识别 aarch64-linux-ohos 平台 | config.guess/config.sub 缺少鸿蒙平台标识 | 补丁 0003-config.guess.patch + 0004-config.sub.patch |
| 2 | configure 中部分检查项对鸿蒙不适用 | configure 脚本的硬编码检查逻辑 | 补丁 0005-configure.patch (umask 077→022) |
| 3 | 上游不提供 pkg-config (.pc) 文件 | autotools AC_OUTPUT 和 Makefile.am 中缺少 pkgconfig  | 补丁 0006-configure.ac.patch + 0001-Makefile.am.patch + 0002-Makefile.in.patch + 0007-libdvbcsa.pc.in.patch |
| 4 | strip 不完全 (.symtab 保留) | 打包流程使用 --strip-debug 仅移除 debug 段 | 使用 --strip-unneeded 替代 --strip-debug |
## 源码修改
应用 7 个补丁：
- `0001-Makefile.am.patch` — 添加 pkgconfig_DATA 安装规则
- `0002-Makefile.in.patch` — 添加 pkgconfigdir/pkgconfig_DATA + install/uninstall kg-configDATA 目规则
- `0003-config.guess.patch` — 添加 aarch64-linux-ohos 平台识别
- `0004-config.sub.patch` — 添加 aarch64-linux-ohos 平台识别
- `0005-configure.patch` — 修正 configure 中 umask (077→022) + 添加 libdvbcsa.pc 输出到 AC_OUTPUT
- `0006-configure.ac.patch` — 添加 libdvbcsa.pc 到 AC_OUTPUT
- `0007-libdvbcsa.pc.in.patch` — 新增 pkg-config 模板文件
## 依赖版本
无外部依赖，仅依赖 libc.so（系统库）。
## 验证结果
### 质量门禁
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py verify-build libdvbcsa 1.1.0
# G1-G4: PASS (全部通过)
```

### 功能测试（24项全部通过）
```bash
# 编译测试程序
aarch64-unknown-linux-ohos-clang -o test_dvbcsa test_dvbcsa.c \
  -I$PREFIX/include -L$PREFIX/lib -ldvbcsa -Wl,-rpath,$PREFIX/lib
# 运行结果: 24 PASS / 0 FAIL
# 覆盖: 密钥分配/释放、CW设置、单包加解密、多长度加解密、  、        CW互斥性、Bitslice批量加解密、密钥切换
```
### 库信息
```bash
file libdvbcsa.so.1.0.1: ELF shared object, 64-bit LSB arm64, stripped
NEEDED: libc.so (仅系统库依赖)
RUNPATH: $ORIGIN:$ORIGIN/external
.codesign section: 存在 (ELF签名完成)
.gnu_debuglink: 存在 (debug符号已分离)
.symtab: 已移除 (使用 --strip-unneeded)
导出符号: dvbcsa_key_alloc/free/set, dvbcsa_encrypt/decrypt,          dvbcsa_bs_key_alloc/free/set, dvbcsa_bs_encrypt/decrypt,          dvbcsa_bs_batch_size 等
pkg-config: PKG_CONFIG_PATH=$PREFIX/lib/pkgconfig pkg-config --modversion libdvbcsa → 1.1.0
```
## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| libdvbcsa-1.1.0-ohos-aarch64.tar.gz | 280KB | Release预编译包 (已strip+签名+pkg-config) |
| libdvbcsa-1.1.0-ohos-aarch64-debug.tar.gz | 32KB | Debug符号包 |
| libdvbcsa.so.1.0.1 | 67480 bytes | 动态库 (stripped+签名+debuglink+RPATH) |
| libdvbcsa.a | 56372 bytes | 静态库 |
| dvbcsa/dvbcsa.h | — | 头文件 |
| libdvbcsa.pc | — | pkg-config 文件 |
## 注意事项
1. **pkg-config已修复**: libdvbcsa.pc 已通过补丁添加到安装流程, `pkg-config --modversion libdvbcsa` 正确返回 1.1.0。
2. **Strip已修复**: 使用 `--strip-unneeded` 替代 `--strip-debug`, .symtab 已完全移除, file 输出 "stripped"。
3. **无 make check**: 此软件为纯库,无自带测试套件。功能验证通过自定义测试程序完成。
4. **共享库+静态库同时生成**: 默认编译产出 .so 和 .a,适合不同链接场景。
---
**编译结束**: 2026-06-03
**最终状态**: published
**功能测试**: 2026-06-03 24/24 PASS
**上库评估**: ✅ 符合上库要求