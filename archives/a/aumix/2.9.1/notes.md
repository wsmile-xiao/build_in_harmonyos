# aumix 2.9.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-29
- 编译器: clang 15.0.4
- 平台: aarch64-unknown-linux-ohos (HarmonyOS)
- 状态: built

## 编译步骤

1. **初始化**：`ohc-run.py init-build aumix 2.9.1 --url=https://sourceforge.net/projects/aumix/files/aumix/2.9.1/aumix-2.9.1.tar.bz2/download --tar=tar.bz2`
   - SSL 证书问题导致下载失败，手动用 `curl -sk -L` 下载到 `$TMPDIR/builds/aumix-2.9.1.tar.bz2`
   - URL 以 `/download` 结尾，需显式指定 `--tar=tar.bz2`
2. **替换 config.guess/config.sub**：原始版本（2008年）无法识别 OHOS 平台，从系统 automake-1.16 复制 2023 年版本
3. **修补 configure umask**：将 configure 脚本中的 `umask 077` 修改为 `umask 022`（HMDFS 兼容性修复，从 configure 源头修复而非仅修补 config.status）
4. **configure**：`./configure --prefix=$DEFAULT_PREFIX --without-gtk`
5. **make**：`make -j1`（-j2 失败：HMDFS 不支持 mkfifo）
6. **修复重复符号**：common.h 中直接定义全局变量 `ourlevel` 和 `our_recplay`（非 extern），clang/LLD 报重复符号。将定义移至 common.c，头文件改为 extern 声明
7. **make install DESTDIR**：staging 隔离安装
8. **make check**：通过（无测试套件）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别平台 | 原始 config.guess 为 2008 年版本，不支持 OHOS | 替换为 automake-1.16 的 config.guess/config.sub (2023年版本) |
| 2 | configure 失败：GTK+ 未找到 | pkg-config 检测到 GTK+ 2.0 但未安装 | 添加 `--without-gtk` 参数 |
| 3 | config.status 创建临时文件失败 | HMDFS 在 umask 077 下创建的目录带 SGID 位，无法写入 | 将 configure 脚本中 `umask 077` 改为 `umask 022`（从源头修复） |
| 4 | 链接错误：重复符号 ourlevel/our_recplay | common.h 头文件中直接定义全局变量（非 extern），多个 .o 文件重复定义 | 将定义移至 common.c，头文件改为 extern 声明（比 -fcommon 更正确的修复） |
| 5 | make -j2 失败 | HMDFS 不支持 mkfifo（make jobserver 通信） | 使用 `make -j1` |

## 源码修改

- `build-aux/config.guess`: 替换为支持 OHOS 平台的版本（来自 automake-1.16）
- `build-aux/config.sub`: 替换为支持 OHOS 平台的版本（来自 automake-1.16）
- `configure`: umask 077 → umask 022（HMDFS 兼容性修复，2处）
- `src/common.h`: `ourlevel` 和 `our_recplay` 改为 extern 声明
- `src/common.c`: 添加 `ourlevel` 和 `our_recplay` 的定义

## 依赖版本

| 依赖 | 版本 |
|------|------|
| ncurses | 未安装（构建无 curses UI，不影响命令行功能） |
| autoconf | 2.72 |
| automake | 1.16.5 |
| clang | 15.0.4 |

## 验证结果

```bash
$ aumix --help
aumix 2.9.1 usage: aumix [-<channel option>[[+|-][<amount>]]|<level>|
R[ecord]|P[lay]|q[uery]] [-dhLqS] [-f <rc file>]]
...
```

## 注意事项

- aumix 需要访问 `/dev/mixer` 设备，在没有音频硬件的环境中 `aumix -q` 可能失败
- 重复符号修复采用 extern 声明方式（比 -fcommon 更规范）
- configure 脚本的 umask 补丁从源头修复，避免每次 configure 后重新打补丁
- ncurses 未安装，aumix 以非交互模式运行（命令行参数模式仍可用）
---

**编译结束**: 2026-06-29 16:29
**最终状态**: built
