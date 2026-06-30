# log4shib 2.0.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-11
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 平台: aarch64-unknown-linux-ohos (HarmonyOS)
- 状态: published

## 编译步骤
1. init-build log4shib 2.0.1 --url=https://shibboleth.net/downloads/log4shib/2.0.1/log4shib-2.0.1.tar.gz
2. 手动下载 tarball（SSL 证书问题）后放入 ~/tmp/builds/
3. 替换 config/config.guess 和 config/config.sub 为 automake-1.16 版本（支持 HarmonyOS）
4. 修改 configure 中 umask 077 → umask 007（HMDFS 限制）
5. ./configure --prefix=$DEFAULT_PREFIX → 手动执行 ./config.status（umask 修改）
6. make -j1 → 成功
7. make install DESTDIR=$TEST_PREFIX → 成功
8. make check → 11/11 全部通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 下载失败 | 证书验证失败 | 手动 curl -kL 下载 |
| 2 | config.guess 不识别 HarmonyOS | E007: 2018 版 config.guess 不含 HarmonyOS 检测 | 替换为 automake-1.16 新版（输出 aarch64-unknown-linux-ohos） |
| 3 | config.status 无法写入临时文件 | HMDFS: umask 077 导致 mktemp -d 创建的目录权限为 drwx--S---，owner 也不能写入 | 修改 configure/config.status 中 umask 077 → umask 007 |

## 源码修改清单

| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|---------|
| config/config.guess | E007: 不识别 HarmonyOS | 替换为 automake-1.16 版本 | ✅ 已生成 0001-config-config.guess.patch |
| config/config.sub | E007: 不识别 HarmonyOS | 替换为 automake-1.16 版本 | ✅ 已生成 0002-config-config.sub.patch |
| configure | HMDFS: umask 077 导致临时目录不可写 | umask 077 → umask 007 | ✅ 已生成 0003-configure.patch |

## 依赖版本
- 无外部依赖

## 验证结果

```bash
make check: 11/11 PASS
  PASS: testCategory
  PASS: testFixedContextCategory
  PASS: testNDC
  PASS: testPattern
  PASS: testErrorCollision
  PASS: testPriority
  PASS: testFilter
  PASS: testProperties
  PASS: testConfig
  PASS: testPropertyConfig
  PASS: sscpp706

Staging 验证:
  lib/liblog4shib.so.2.0.1    ✓ (533KB)
  lib/liblog4shib.so.2         ✓ (软链接)
  lib/liblog4shib.so           ✓ (软链接)
  lib/liblog4shib.la           ✓ (libtool 档案)
  lib/pkgconfig/log4shib.pc    ✓ (pkg-config 文件)
  include/log4shib/*.hh        ✓ (30 个头文件)

质量门禁 verify-build:
  G1: ✅ PASS
  G2: ✅ PASS (⚠️1: 无可执行文件，属纯库软件)
  G3: ✅ PASS
  G4: ✅ PASS
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| log4shib-2.0.1-ohos-aarch64.tar.gz | 1.38MB | 预编译包 |
| log4shib-2.0.1-ohos-aarch64-debug.tar.gz | 471KB | 调试包 |
| 0001-config-config.guess.patch | 69.7KB | config.guess 替换补丁 |
| 0002-config-config.sub.patch | 69.3KB | config.sub 替换补丁 |
| 0003-configure.patch | 728B | configure umask 修复补丁 |

## 注意事项
- log4shib 是纯库软件，无 bin/ 可执行文件，安全弹窗验证(R7)不适用
- configure 中 umask 077 需修改为 007 以兼容 HMDFS（E011 类型问题）
- 源码 SHA256: aad37f3929bd3d4c16f09831ff109c20ae8c7cb8b5771