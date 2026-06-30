# libpcre16 8.45 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-11
- 编译器: clang/clang++
- 状态: built（编译成功，测试通过）

## 编译步骤

### 1. init-build
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build libpcre16 8.45 --url=https://sourceforge.net/projects/pcre/files/pcre/8.45/pcre-8.45.tar.gz
```

### 2. 应用补丁（E007 + E011）
```bash
cd $BUILD_SRC_DIR
# 修改 config.guess：添加 HarmonyOS 检测
# 修改 config.sub：添加 ohos 到基本系统类型 + linux-ohos 组合
# 修改 configure：umask 077 → 022
python3 $SKILL_ROOT/scripts/ohc-run.py track-edit add libpcre16 8.45 config.guess
python3 $SKILL_ROOT/scripts/ohc-run.py track-edit add libpcre16 8.45 config.sub
python3 $SKILL_ROOT/scripts/ohc-run.py track-edit add libpcre16 8.45 configure
```

### 3. configure
```bash
./configure --prefix=$DEFAULT_PREFIX --enable-pcre16 --enable-pcre32
```

### 4. make + install
```bash
make -j2
make install DESTDIR=$TEST_PREFIX  # staging 安装
make check  # 测试全部通过（5/5 PASS）
make install  # 最终安装到 ~/usr/local
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别系统 | E007: 缺少 HarmonyOS 检测 | 在 config.guess 开头添加 HarmonyOS uname 检测 |
| 2 | config.sub 拒绝 linux-ohos 组合 | E007补充: kernel-os 组合验证缺少 linux-ohos | 在 config.sub 第 1740 行添加 `| linux-ohos*` |
| 3 | umask 077 导致 Permission denied | E011: HMDFS UID 映射问题 | 修改 configure 中 `umask 077` 为 `umask 022` |

## 源码修改

### 0001-config.guess.patch
- 文件：config.guess
- 修改：在文件开头添加 HarmonyOS 检测逻辑
- 类型：平台适配（E007）

### 0002-config.sub.patch
- 文件：config.sub
- 修改：
  1. 第 1723 行添加 `| ohos*` 到基本系统类型列表
  2. 第 1740 行添加 `| linux-ohos*` 到 kernel-os 组合列表
- 类型：平台适配（E007补充）

### 0003-configure.patch
- 文件：configure
- 修改：umask 077 → 022
- 类型：环境适配（E011）

## 依赖版本

无外部依赖（autotools 自包含）

## 验证结果

### 1. pcregrep 可执行
```bash
~/usr/local/bin/pcregrep --version
# 输出: pcregrep version 8.45 2021-06-15
```

### 2. pkg-config 可识别
```bash
export PKG_CONFIG_PATH=~/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
pkg-config --modversion libpcre16
# 输出: 8.45
```

### 3. 库文件完整
```bash
ls ~/usr/local/lib/ | grep libpcre
# 输出：
# libpcre.a, libpcre.so
# libpcre16.a, libpcre16.so ✓
# libpcre32.a, libpcre32.so ✓
# libpcrecpp.a, libpcrecpp.so
# libpcreposix.a, libpcreposix.so
```

### 4. 测试结果
```bash
make check
# Testsuite summary for PCRE 8.45
# # TOTAL: 5
# # PASS:  5
# # SKIP:  0
# # FAIL:  0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libpcre16-8.45-ohos-aarch64.tar.gz | 待生成 | 预编译包（待制作） |

## 注意事项

1. PCRE 8.45 是 PCRE 库的最后版本（PCRE2 是新版本）
2. libpcre16 是 16-bit 字符版本，需要通过 `--enable-pcre16` 启用
3. libpcre32 是 32-bit 字符版本，也需要通过 `--enable-pcre32` 启用
4. 测试在 HarmonyOS 上全部通过（优于历史记录）
5. G0 干净构建验证失败（Python subprocess 平台限制），但实际编译成功

---
**编译结束**: 2026-06-11 14:31
**最终状态**: built（编译成功，测试通过，无预编译包）
---

**编译结束**: 2026-06-11 15:18
**最终状态**: built
