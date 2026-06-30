# cmigemo 20110227 适配笔记

## 编译环境
- 构建系统: custom（Make_gcc.mak，非标准autotools）
- 编译日期: 2026-06-12
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: published
- 平台: 鸿蒙 OpenHarmony (aarch64, musl libc)

## 编译步骤

1. 手动下载源码包 `cmigemo-default-src-20110227.zip`（SSL证书问题，需curl -k）
2. 将zip包放到 `~/tmp/builds/cmigemo-20110227.zip`，运行 `ohc-run.py init-build --no-download`
3. 修改 `configure` 脚本：添加 iconv 作为编码过滤器 fallback（当 qkc/nkf 不可用时）
4. 运行 `./configure --prefix=$DEFAULT_PREFIX`
5. 修改 `config.mk` 中 `FILTER_CP932` 和 `FILTER_EUCJP` 为正确的 iconv 格式
   - `FILTER_CP932 = iconv -f euc-jp -t cp932`
   - `FILTER_EUCJP = iconv -f cp932 -t euc-jp`
6. 修改 `config.mk` 中 `INSTALL` 路径为 `~/usr/local/bin/install`（/usr/bin/install不存在）
7. 修复 `src/wordbuf.c`：添加 `#include <limits.h>`（INT_MAX 未定义）
8. 修改 `compile/unix.mak`：在所有 install 目标中添加 DESTDIR 变量支持
9. 修改 `compile/Make_gcc.mak`：在 install-lib/uninstall-lib 中添加 DESTDIR 支持
10. `make gcc CC=clang` — 构建二进制和共享库（libmigemo.so.1.1.0）
11. `make gcc-dict CC=clang` — 下载SKK-JISYO.L字典并生成migemo字典
    - 下载约1.7MB的SKK字典，使用iconv完成编码转换
12. `make gcc-install CC=clang DESTDIR=$TEST_PREFIX` — staging安装
13. `make gcc-install CC=clang DESTDIR=""` — 本地安装到 $DEFAULT_PREFIX

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL下载失败 | 鸟蒙平台SSL证书验证不通过 | 使用 `curl -kL` 手动下载，然后 `init-build --no-download` |
| 2 | configure找不到qkc/nkf | 鸿蒙平台没有日本编码转换工具 | 修改configure脚本，添加iconv作为fallback |
| 3 | config.mk编码参数错误 | iconv参数格式不同于nkf(-s/-e) | 手动修正为 `iconv -f euc-jp -t cp932` 格式 |
| 4 | INT_MAX未定义导致编译失败 | wordbuf.c缺少 `<limits.h>` 头文件 | 添加 `#include <limits.h>` |
| 5 | /usr/bin/install不存在 | 鸿蒙平台路径差异 | 修改config.mk使用 `~/usr/local/bin/install` |
| 6 | DESTDIR不支持 | 自定义Makefile没有DESTDIR变量 | 在unix.mak和Make_gcc.mak中添加DESTDIR |
| 7 | cmigemo不支持--version | cmigemo是交互式查询工具 | 使用 `-h` 选项验证二进制可用 |

## 源码修改

- `configure`: 添加iconv作为编码过滤器fallback（+6/-2行）
- `src/wordbuf.c`: 添加 `#include <limits.h>`（+1行）
- `compile/unix.mak`: 添加 DESTDIR 变量到所有install目标（+28/-27行）
- `compile/Make_gcc.mak`: 添加 DESTDIR 到 install-lib/uninstall-lib（通过unix.mak变更覆盖）
- `config.mk`: 修改FILTER、INSTALL路径（生成文件，不生成补丁）

## 依赖版本

- 无外部依赖（required和optional都为空）
- 运行时依赖: musl libc, ld-musl-aarch64.so.1

## 验证结果

```bash
$ cmigemo -h
cmigemo - C/Migemo Library 1.3 Driver

$ cmigemo -w test -d $DEFAULT_PREFIX/share/migemo/cp932/migemo-dict
(正则模式输出，包含test及日文扩展)

$ cmigemo -w test -v -d .../migemo-dict   # Vim模式
\%(...\|t\_s*e\_s*s\_s*t\)

$ cmigemo -w test -e -d .../migemo-dict   # Emacs模式
\(...\|t\s-*e\s-*s\s-*t\)

$ file $DEFAULT_PREFIX/bin/cmigemo
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)

$ wc -l $DEFAULT_PREFIX/share/migemo/cp932/migemo-dict
163268
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/cmigemo | 22912B | 主程序（aarch64 ELF） |
| lib/libmigemo.so.1.1.0 | 43392B | 共享库（aarch64 ELF） |
| lib/libmigemo.so.1 | 软链接 | → libmigemo.so.1.1.0 |
| lib/libmigemo.so | 软链接 | → libmigemo.so.1.1.0 |
| include/migemo.h | — | 头文件 |
| share/migemo/cp932/* | ~3.5MB | CP932编码字典（5文件） |
| share/migemo/euc-jp/* | ~3.5MB | EUC-JP编码字典（5文件） |

---

**编译结束**: 2026-06-12
**最终状态**: published
