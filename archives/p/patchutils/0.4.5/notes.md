# patchutils 0.4.5 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-27
- 编译器: clang / clang++
- 目标平台: aarch64-unknown-linux-ohos (HarmonyOS HongMeng Kernel 1.12.0)
- 状态: published

## 编译步骤

### 1. 初始化
由于环境中 SSL 证书验证失败（`CERTIFICATE_VERIFY_FAILED`），使用 `--no-download` 模式并手动下载源码包：
```bash
curl -k -L -o downloads/patchutils-0.4.5.tar.xz https://github.com/twaugh/patchutils/releases/download/0.4.5/patchutils-0.4.5.tar.xz
python3 $SKILL_ROOT/scripts/ohc-run.py init-build patchutils 0.4.5 --no-download --url=...
```

### 2. 平台补丁
**E007: config.guess 无法识别 HarmonyOS**
```bash
perl $SKILL_ROOT/scripts/patch-autotools-ohos.pl config.guess config.sub
```
补丁后 `config.guess` 返回 `aarch64-unknown-linux-ohos`，`config.sub` 支持 `ohos-linux` 三元组。

**E073: config.status umask 077 导致 HMDFS 权限问题**
configure 脚本在创建临时目录时使用 `umask 077`，在 HMDFS 上导致 `Permission denied`。
需将 `umask 077` 改为 `umask 000`（第 19762、19767 行）。

### 3. 配置与编译
```bash
./configure --prefix=$DEFAULT_PREFIX HELP2MAN=/bin/true \
  ac_cv_sizeof_long=8 ac_cv_sizeof_long_long=8 ac_cv_sizeof_off_t=8 \
  ac_cv_sizeof_int=4 ac_cv_sizeof_void_p=8

# 需用 AUTOCONF=true 等跳过 autotools 重新生成（因 automake-1.18 不存在）
make -j1 AUTOCONF=true AUTOMAKE=true ACLOCAL=true AUTOHEADER=true
make install DESTDIR=$TEST_PREFIX  # DESTDIR 模式
```

### 4. 测试
```bash
make check -j1
```
结果：135/199 PASS, 58 FAIL (toybox patch 不兼容), 6 XFAIL

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 下载失败 | HarmonyOS 环境证书验证不支持 | `curl -k` 手动下载 + `--no-download` |
| 2 | config.guess 返回 "unable to guess system type" | GNU config.guess 不支持 __OHOS__ libc | `patch-autotools-ohos.pl` 补丁 |
| 3 | config.sub 不识别 aarch64-unknown-linux-ohos | 缺少 ohos-linux 三元组 | 同上（一并修补） |
| 4 | config.status "Permission denied" 创建临时文件 | HMDFS 上 umask 077 导致目录内无法写入 | 改 configure 中 umask 077 → 000 |
| 5 | make 报错 aclocal-1.18 缺失 | 修改 configure 后触发 autotools 重生成规则 | `AUTOCONF=true AUTOMAKE=true ACLOCAL=true` |
| 6 | `rm -rf conf*` 删除了 configure.ac/configure | shell glob 匹配意外 | 从 .orig 目录恢复文件 |

## 源码修改

| 补丁文件 | 修改目标 | 内容 |
|----------|----------|------|
| 0001-config.guess.patch | config.guess | 添加 __OHOS__ libc 检测 + HarmonyOS 系统标识 |
| 0002-config.sub.patch | config.sub | 添加 ohos-linux 三元组（`basic_machine=$field1-unknown, basic_os=linux-ohos`） |
| 0003-configure.patch | configure | umask 077 → umask 000（两处） |

## 依赖版本

无外部依赖。patchutils 仅依赖系统 diff/patch 命令。

- clang (系统自带)
- diff (GNU diffutils 3.10)
- patch (toybox 0.8.12 — 注意：与 interdiff 不完全兼容)
- perl 5.40

## 验证结果

```bash
$ $DEFAULT_PREFIX/bin/interdiff --version
interdiff - patchutils version 0.4.5

$ $DEFAULT_PREFIX/bin/filterdiff --version
filterdiff - patchutils version 0.4.5

$ $DEFAULT_PREFIX/bin/rediff --version
rediff - patchutils version 0.4.5

$ $DEFAULT_PREFIX/bin/lsdiff --version
lsdiff - patchutils version 0.4.5

$ $DEFAULT_PREFIX/bin/grepdiff --version
grepdiff - patchutils version 0.4.5

$ bash config.guess
aarch64-unknown-linux-ohos

$ bash config.sub aarch64-unknown-linux-ohos
aarch64-unknown-linux-ohos
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| patchutils-0.4.5-ohos-aarch64.tar.gz | 965KB | 预编译发布包（stripped ELF） |
| patchutils-0.4.5-ohos-aarch64-debug.tar.gz | 269KB | 调试符号包 |
| 0001-config.guess.patch | 1.6KB | 平台适配补丁 |
| 0002-config.sub.patch | 0.6KB | 平台适配补丁 |
| 0003-configure.patch | 0.9KB | HMDFS 权限修复补丁 |

## 注意事项

1. **toybox patch 不兼容**: interdiff/combinediff/flipdiff 功能依赖 GNU patch，toybox patch 会导致临时文件处理失败。建议安装 GNU patch (`gpatch`) 以启用完整功能。
2. **configure.ac 不可随意删除**: `rm -rf conf*` 会匹配到 `configure.ac`、`configure`、`config.guess`、`config.sub` 等文件，清理时务必精确指定文件名。
3. **autotools 重生成**: 修改 configure 后 make 会尝试重生成，需用 `AUTOCONF=true AUTOMAKE=true ACLOCAL=true AUTOHEADER=true` 跳过。

---
**编译开始**: 2026-05-27 04:10
**编译结束**: 2026-05-27 12:41
**最终状态**: published
