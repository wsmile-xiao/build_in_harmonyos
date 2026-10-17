# aj (aj-snapshot) 0.9.9 适配笔记

## 概述

**软件**: aj-snapshot 0.9.9（JACK/ALSA MIDI 连接快照/恢复工具）
**上游**: https://gitlab.com/aj-snapshot/aj-snapshot（SourceForge 分发）
**构建系统**: autotools（configure.ac + Makefile.am），单可执行 aj-snapshot
**状态**: built

## 依赖分析（configure.ac 硬性 REQUIRED）

| 依赖 | 版本 | 来源 | 说明 |
|------|------|------|------|
| alsa-lib | 1.2.12 | cmd-pkgs 预编译包 | `AC_CHECK_LIB(asound)` REQUIRED |
| jack | 1.9.22 | cmd-pkgs 预编译包 | `AC_CHECK_LIB(jack)` REQUIRED |
| mxml | 4.0.4 | 配方内自包含构建 | `AC_CHECK_LIB(mxml, mxmlLoadFile)` REQUIRED |

三个依赖均已在 build_in_harmonyos main 中合入适配记录（alsa-lib 1.2.16.1 有 conan 配方、
jack 1.9.22 / mxml 4.0.4 有 manifest+notes+patches）。aj 配方以 cmd-pkgs 预编译包
（alsa-lib/jack）+ 自包含构建（mxml）方式获取，无需等待任何未合入依赖。

## 关键适配点

### 1. mxml 4.0.4 传统布局（--disable-libmxml4-prefix）

aj-snapshot 0.9.9 按 mxml v3 接口编写：`#include <mxml.h>`、`-lmxml`、`PKG_CHECK_MODULES([MXML], [mxml])`。
mxml 4.0.4 默认安装为 **libmxml4 前缀**：
- 头文件 → `include/libmxml4/mxml.h`
- 库 → `libmxml4.a` / `libmxml4.so`
- pkg-config → `mxml4.pc`

aj-snapshot 找不到 mxml.h / -lmxml / mxml.pc → configure 报错。
解法：mxml configure 加 **--disable-libmxml4-prefix** 恢复传统布局（mxml.h / libmxml / mxml.pc）。

### 2. mxml 4.x API 差异（补丁 0001/0002）

- `MXML_NO_DESCEND` 宏被 `mxml_descend_t` 枚举取代（`MXML_DESCEND_NONE`，值 0 语义等价）：
  aj-jack.c / aj-alsa.c 共 6 处 `mxmlFindElement(..., MXML_NO_DESCEND)` → `MXML_DESCEND_NONE`
- `mxmlLoadFile(top, FILE*, callback)` → `mxmlLoadFile(top, mxml_options_t*, FILE*)`：
  aj-file.c 的 `mxmlLoadFile(NULL, file, MXML_TEXT_CALLBACK)` → `mxmlLoadFile(NULL, NULL, file)`
  （MXML_TEXT_CALLBACK 在 4.x 已移除，options 传 NULL 用默认）
- `mxmlSaveFile(node, FILE*, ws_cb)` → `mxmlSaveFile(node, mxml_options_t*, FILE*)`：
  需 `mxmlOptionsNew()` + `mxmlOptionsSetWhitespaceCallback(options, cb, NULL)` 再保存；
  whitespace 回调签名也改为 `(void *cbdata, mxml_node_t*, mxml_ws_t)`
- 对应头文件 aj-file.h 中 xml_whitespace_cb 声明同步更新

### 3. config.guess / config.sub 不需要附带（实测确认）

aj-snapshot tarball **不含** config.guess / config.sub，但 configure.ac **无 AC_CANONICAL_* 宏**
（不实际执行 config.guess），本地实测：不附带这两个文件，configure + make 全链路构建通过
（rc=0，src/aj-snapshot 正常生成）。因此配方**不附带** config.guess/config.sub
（避免约 87KB 冗余文件）；mxml 自包含构建所需的 config.guess/sub 补丁（mxml-0001/0002）仍保留。

### 4. HMDFS umask 077 权限限制

configure 创建临时目录用 `umask 077`，HMDFS 上 `config.status: can't create ./confXXXXXX/subs1.awk: Permission denied`。
解法：补丁 0003 将 configure 中 2 处 `umask 077` 改为 `umask 000`（与 mxml/abook 同款修复）。

### 5. 依赖安装（cmd-pkgs 预编译包）

aj 配方 generate() 用纯 Python（urllib + tarfile，不依赖 curl）安装：
- `alsa-lib-1.2.12-ohos-aarch64.tar.gz` → prefix/lib/libasound.so.2 + include/alsa/asoundlib.h + pkgconfig/alsa.pc
- `jack-1.9.22-ohos-aarch64.tar.gz` → prefix/lib/libjack.so.0 + include/jack/jack.h + pkgconfig/jack.pc

mxml 自包含构建后同样安装到 prefix（libmxml.a + include/mxml.h + pkgconfig/mxml.pc）。

## 构建步骤（本地验证通过）

1. `generate()`：cmd-pkgs 安装 alsa-lib 1.2.12 + jack 1.9.22 到 prefix
2. `_build_mxml()`：应用 mxml 3 补丁 → configure `--disable-libmxml4-prefix --enable-static --disable-shared` → make → make install
3. `apply_conandata_patches()`：应用 aj 3 补丁（0001/0002/0003）
4. `./configure --prefix=prefix`（PKG_CONFIG_PATH/CPPFLAGS/LDFLAGS 指向 prefix；无 AC_CANONICAL 宏，无需 config.guess/config.sub）
5. `make` → src/aj-snapshot（aarch64 ELF，not stripped）

## 上游测试情况

上游 0.9.9 tarball **无测试框架**：
- 无 test/ 目录
- 无 make check / make test 目标（Makefile.am 仅 SUBDIRS = src man）
- configure.ac 仅做依赖头文件/库检查（asound/jack/mxml REQUIRED）

因此上游测试用例 0 个，通过率 0/0（不适用）。适配后以 test_package 的
`aj-snapshot -h` 冒烟测试作为消费测试（R34 反空壳：真实调用被测包二进制）。

## 验证结果

- 编译状态：通过（本地 clang 15.0.4 构建 src/aj-snapshot 成功，aarch64 ELF）
- 上游测试用例通过率：0/0（上游无测试用例）
- test_package：aj-snapshot -h 打印 usage 校验通过
- 依赖：alsa-lib 1.2.12 / jack 1.9.22（cmd-pkgs 预编译包）+ mxml 4.0.4（自包含构建）

---

**编译验证**: 2026-08-12
**最终状态**: built
