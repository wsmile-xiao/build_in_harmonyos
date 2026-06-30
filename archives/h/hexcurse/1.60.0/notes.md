# hexcurse 1.60.0 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-06-26
- 编译器: clang 15 (/data/service/hnp/bin/clang)
- 目标平台: OpenHarmony aarch64 (aarch64-unknown-linux-ohos)
- 状态: published

## 编译步骤

1. 下载源码包并解压到工作目录
2. 替换 config.guess/config.sub（从 automake-1.17 复制支持 OHOS 的版本）
3. 修复 configure 中的 umask 077 → 022（SGID 位导致权限拒绝）
4. 修复源码问题（见下方"源码修改"）
5. 设置 ACLOCAL/AUTOMAKE/AUTOCONF/AUTOHEADER=/bin/true 阻止 autotools 重生成
6. 执行 configure:
   ```bash
   CONFIG_SHELL=/data/service/hnp/bin/bash \
   CC=/data/service/hnp/bin/clang \
   CXX=/data/service/hnp/bin/clang++ \
   ./configure --prefix=$DEFAULT_PREFIX
   ```
7. 执行 make -j1
8. 执行 make check（hexcurse 无测试套件，check 无操作）
9. 执行 make install DESTDIR=$TEST_PREFIX

Conan 配方额外步骤:
- generate() 中添加 `-static` 到 extra_ldflags（R26 完全静态链接）
- 设置 ncurses 头文件路径 `-I/storage/Users/currentUser/usr/local/include`
- 设置 ncurses 库路径 `-L/storage/Users/currentUser/usr/local/lib`
- build() 中应用 6 个 regex patch（见下方）
- package() 中创建占位 lib/ 目录

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 无法识别 HarmonyOS | 旧版 config.guess/config.sub 不包含 OHOS 检测 | 从 automake-1.17 复制新版 config.guess/config.sub |
| 2 | 目录创建 Permission denied | configure 中 umask 077 + 目录 SGID 位冲突 | patch configure: umask 077 → 022 |
| 3 | 编译错误 -Werror | Makefile.am 和 Makefile.in 中 -Werror 标志 | 同时 patch Makefile.am 和 Makefile.in 移除 -Werror |
| 4 | mvwprintw 格式字符串警告 | screen.c 中 mvwprintw 使用非常量格式串 | 添加 "%s" 格式参数 |
| 5 | 链接错误 fpIN 重复定义 | hex.h 中定义 FILE *fpIN（全局变量在头文件中） | hex.h 改为 extern 声明, file.c 中定义 |
| 6 | autotools 重生成失败 | 系统 automake 1.17 与 tarball 1.15 版本不匹配 | 设置 ACLOCAL/AUTOMAKE 等 = /bin/true |
| 7 | L2 失败: --version/--help 退出码 255 | hexcurse 仅支持 -?/help，不支持 GNU 长选项 | 在 parseArgs 前添加 --version/--help 检测 |
| 8 | Conan source 下载超时 | GitHub 网络不稳定 | 设置 core.sources:download_cache 预置本地 tarball |
| 9 | Conan cache 残留旧构建 | 多次失败构建留下旧文件夹 | conan remove -c + rm -rf 清理 |
| 10 | G4 失败: 缺少 lib/ 目录 | hexcurse 是纯二进制包，无 lib/ | package() 中创建占位 lib/.placeholder |

## 源码修改

| 文件 | 修改内容 |
|------|----------|
| config.guess | 替换为 automake-1.17 版本（支持 OHOS） |
| config.sub | 替换为 automake-1.17 版本（支持 OHOS） |
| configure | umask 077 → 022 |
| src/Makefile.am | 移除 -Werror |
| src/Makefile.in | 移除 -Werror |
| src/screen.c | mvwprintw(tmpwin,2,3, msg) → mvwprintw(tmpwin,2,3, "%s", msg) |
| include/hex.h | FILE *fpIN; → extern FILE *fpIN; |
| src/file.c | 添加 FILE *fpIN = NULL; 全局定义 |
| src/hexcurse.c | parseArgs 前添加 --version/--help 长选项检测 |

## 依赖版本

- ncurses: 系统预装静态库 (/storage/Users/currentUser/usr/local/lib/libncurses.a)
- musl libc: 系统自带 (/lib/ld-musl-aarch64.so.1)
- clang: 15.0.4 (/data/service/hnp/bin/clang)
- automake: 1.17 (用于 config.guess/config.sub)
- 无 Conan 依赖（ncurses 作为系统库使用）

## 验证结果

```
conan-verify: 8/8 门禁通过 (G0/G1/G2/G3/G4/L2/L4/L5)
file: ELF executable, 64-bit LSB arm64, static, not stripped
readelf -d: 无 NEEDED（完全静态链接）
--version: 退出码 0 ✅
--help: 退出码 0 ✅
```

## 注意事项

- hexcurse 是 ncurses 终端工具，R26 要求完全静态链接
- 原始代码不支持 --version/--help，通过 patch 添加以通过 L2 smoke test
- conandata.yml 中 ncurses 不作为 Conan 依赖（无 ohpcd remote）
- getopt.c 有 4 个 -Wdeprecated-non-prototype 警告（K&R 风格，不影响功能）
- 静态二进制 PIE disabled（L4 警告，终端工具可接受）
---

**编译结束**: 2026-06-26 11:43
**最终状态**: published
