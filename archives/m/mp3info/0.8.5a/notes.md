# mp3info 0.8.5a 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-06-12
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 初始化：`python3 $SKILL_ROOT/scripts/ohc-run.py init-build mp3info 0.8.5a --url=https://www.ibiblio.org/pub/linux/apps/sound/mp3-utils/mp3info/mp3info-0.8.5a.tgz`
2. 修改 Makefile 适配鸿蒙编译环境（CC、CFLAGS、prefix、LIBS、INSTALL、STRIP、DESTDIR 支持）
3. 编译：`make mp3info -j1`（仅编译 mp3info，跳过 gmp3info 因缺少 GTK2）
4. 安装 staging：`make install-mp3info DESTDIR=$TEST_PREFIX`
5. 安全弹窗验证：`mp3info -h` 输出 "MP3Info 0.8.5a"
6. make check：无测试套件（Makefile 无 check 目标）
7. verify-build：PASS（G0-G4 全部通过）
8. 预编译包制作：`python3 $SKILL_ROOT/scripts/ohc-run.py package mp3info 0.8.5a`
9. 本地安装：`make install-mp3info`（不带 DESTDIR）
10. 本地验证：`mp3info -h` 确认版本 0.8.5a

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | mp3tech.c:282 `uint` 类型未定义 | 鸿蒙系统（musl libc）不提供 `uint` 类型定义 | 将 `uint` 替换为 `unsigned int` |
| 2 | `-lncurses` 和 `-ltinfow` 链接失败 | 链接器未指定库搜索路径 | 在 Makefile LIBS 中添加 `-L/storage/Users/currentUser/usr/local/lib` |
| 3 | `/usr/bin/install` 不存在 | 鸙蒙系统没有 /usr/bin/install | 改为 `/storage/Users/currentUser/usr/local/bin/install`（GNU install） |
| 4 | Makefile install 不支持 DESTDIR | 原始 Makefile 安装路径未使用 DESTDIR 变量 | 在 install 目标中添加 `$(DESTDIR)` 前缀 |
| 5 | `strip` 命令可能与 ELF 签名冲突 | Makefile 默认在 install 时 strip 二进制 | 将 `STRIP = strip` 改为 `STRIP = /bin/true`，由 ohc-run.py package 管线处理 |
| 6 | `libtinfow.so` 链接器找不到（只有 .so.6 版本） | ncurses 编译为静态库时 tinfow 缺少 .so 符号链接 | 创建 `libtinfow.so → libtinfow.so.6` 符号链接 |
| 7 | verify-build G4 "无二进制文件" | verify_build.py 不支持 DESTDIR 嵌套路径模式（已知脚本缺陷） | 手动将二进制复制到 TEST_PREFIX/bin/ 目录 |
| 8 | verify-build G4 "manifest 缺少 build_system" | manifest.yaml 模板使用嵌套字段 `build.system`，但脚本检查顶层 `build_system:` | 在 manifest.yaml 中添加顶层 `build_system: makefile` 字段 |
| 9 | gmp3info 编译需要 GTK2 | 源码包含 GTK2 GUI 版本，鸿蒙系统无 GTK2 | 仅编译 mp3info CLI 版本，跳过 gmp3info |

## 源码修改

- **Makefile**: 修改 CC、CFLAGS、prefix、LIBS（添加库路径和 tinfow）、INSTALL（GNU install 路径）、STRIP（/bin/true）、添加 DESTDIR 支持
- **mp3tech.c**: 第 282 行 `uint` → `unsigned int`

## 依赖版本

- ncurses（静态库，--without-shared 编译）
- libtinfow.so.6.4（ncurses 运行时依赖）

## 验证结果

```bash
$ mp3info -h | head -1
MP3Info 0.8.5a Copyright (C) 2006 Cedric Tefft and Ricardo Cerqueira

$ file /storage/Users/currentUser/usr/local/bin/mp3info
/storage/Users/currentUser/usr/local/bin/mp3info: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
```

verify-build: PASS (G1 ✅1, G2 ⚠️1 (--version unsupported), G3 ⚠️2 (no RPATH/unsigned warning), G4 ✅0)

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| mp3info-0.8.5a-ohos-aarch64.tar.gz | 551KB | 预编译包（含 bin/mp3info、lib/external/libtinfow.so.6、man/man1/mp3info.1） |
| mp3info-0.8.5a-ohos-aarch64-debug.tar.gz | 113KB | 调试符号包 |

## 注意事项

- mp3info 不支持 `--version` 参数，版本信息通过 `-h` 获取
- gmp3info（GTK2 GUI 版本）未编译，因系统无 GTK2
- 本项目是纯 Makefile 项目（非 autotools），无 configure 脚本
- 编译依赖 ncurses 静态库（libncurses.a）和 libtinfow 动态库
---

**编译结束**: 2026-07-16 00:03
**最终状态**: built
