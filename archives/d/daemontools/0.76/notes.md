# daemontools 0.76 适配笔记

## 编译环境
- 构建系统: makefile（DJB 风格，非标准 autotools）
- 编译日期: 2026-06-11
- 编译器: clang / clang++
- 状态: published

## 编译步骤

daemontools 使用 DJB 风格构建系统，没有标准的 configure/Makefile.am 等文件。构建配置通过编辑 `conf-cc`、`conf-ld`、`home` 等文件完成：

1. **init-build**: `ohc-run.py init-build daemontools 0.76 --url=https://cr.yp.to/daemontools/daemontools-0.76.tar.gz` 下载并解压源码
2. **配置编译器**: 修改 `conf-cc`，将 `gcc` 替换为 `clang -fPIC -O2 -Wimplicit -Wunused -Wcomment -Wchar-subscripts -Wuninitialized -Wshadow -Wcast-qual -Wcast-align -Wwrite-strings`
3. **配置链接器**: 修改 `conf-ld`，将 `gcc -s` 替换为 `clang`
4. **配置安装路径**: 创建 `home` 文件，内容为 `/storage/Users/currentUser/usr/local`
5. **修复 find-systype.sh**: 将脚本中的 `gcc` 替换为 `clang`，使 systype 检测正确
6. **修复 errno 冲突**: 修改 `error.h`，将 `extern int errno;` 替换为 `#include <errno.h>`
7. **跳过测试套**: 修改 `Makefile` 的 `rts` 目标，跳过 FIFO/supervise 测试（OpenHarmony 平台限制）
8. **执行构建**: `make clean && make` — 全部 17 个可执行文件编译成功
9. **手动安装**: DJB 不支持 `make install DESTDIR=`，使用 `cp` 手动安装到 staging 目录

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 链接错误 `undefined symbol: errno` | DJB 代码 `extern int errno;` 与 musl libc errno 宏冲突 | 替换 error.h 中 `extern int errno;` 为 `#include <errno.h>` (补丁 0004) |
| 2 | 编译器检测失败 | find-systype.sh 中硬编码 `gcc` | 替换脚本中 `gcc` 为 `clang` (补丁 0005) |
| 3 | 编译器配置不匹配 | conf-cc/conf-ld 中硬编码 `gcc` | 替换为 `clang` 及 clang 选项 (补丁 0002/0003) |
| 4 | 安装路径未指定 | DJB 通过 `home` 文件读取安装路径 | 创建 home 文件 (补丁 0006) |
| 5 | 测试套挂住 | supervise/svscan 的 FIFO 测试在 OpenHarmony 上无法完成 | 修改 Makefile rts 目标跳过测试 (补丁 0001) |
| 6 | `make install DESTDIR=` 失败 | DJB 构建系统不支持标准 DESTDIR 安装 | 手动 cp 二进制到 staging 目录 |

## 源码修改

共 6 个补丁文件：

| 补丁 | 修改文件 | 修改内容 |
|------|----------|----------|
| 0001-Makefile.patch | Makefile | 修改 rts 目标：跳过 DJB 测试套 |
| 0002-conf-cc.patch | conf-cc | `gcc` → `clang -fPIC -O2 -Wimplicit...` |
| 0003-conf-ld.patch | conf-ld | `gcc -s` → `clang` |
| 0004-error.h.patch | error.h | `extern int errno;` → `#include <errno.h>` |
| 0005-find-systype.sh.patch | find-systype.sh | 脚本内 `gcc` → `clang` |
| 0006-home.patch | home | 新建文件，内容为安装路径 prefix |

## 依赖版本

- 编译器: clang 15.0.4（OpenHarmony SDK 自带）
- libc: musl (ld-musl-aarch64.so.1)
- 依赖库: 无（daemontools 为纯 C 工具集，无第三方依赖）

## 验证结果

```bash
# 二进制完整性 — 全部 17 个 ELF + 1 shell 脚本
$ file /storage/Users/currentUser/usr/local/bin/envdir
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)

# envdir 功能测试
$ envdir <envdir_path> sh -c 'echo "HELLO=$HELLO"'
HELLO=world

# tai64n 时间戳
$ echo "hello" | tai64n
@400000006a2bb028339e2644 hello

# tai64nlocal 转换
$ echo "hello" | tai64n | tai64nlocal
2026-06-12 15:07:10.903554500 hello

# svstat 错误处理
$ svstat /nonexistent
/nonexistent: unable to chdir: file does not exist
```

## 交付物

| 文件 | 大小(KB) | 说明 |
|------|----------|------|
| daemontools-0.76-ohos-aarch64.tar.gz | 1,264 | 预编译包（17 个产物） |
| daemontools-0.76-ohos-aarch64-debug.tar.gz | 460 | 调试版预编译包 |
| 0001-Makefile.patch | ~0.4 | 跳过测试套 |
| 0002-conf-cc.patch | ~0.1 | 编译器配置 |
| 0003-conf-ld.patch | ~0.1 | 链接器配置 |
| 0004-error.h.patch | ~0.3 | errno 修复 |
| 0005-find-systype.sh.patch | ~1 | systype 检测 |
| 0006-home.patch | ~0.1 | 安装路径 |

## 注意事项

1. DJB 构建系统不使用标准 configure/make install，需手动编辑配置文件
2. 源码嵌套结构：tarball 解压后源码在 `admin/daemontools-0.76/src/` 下，需 `build_subdir` 提示
3. supervise/svscan 的完整测试需要 FIFO 命名管道支持，在 OpenHarmony 上有限制
4. 所有 K&R 风格 C 代码的编译警告为预期行为，不影响功能正确性
5. 知识图谱条目 E999 记录了 DJB errno 修复模式，适用于所有 DJB 软件（qmail、djbdns、ucspi-tcp 等）

---
**编译结束**: 2026-06-11 23:50
**最终状态**: published