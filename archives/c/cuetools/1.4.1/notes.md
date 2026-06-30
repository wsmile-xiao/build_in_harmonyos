# cuetools 1.4.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-03
- 编译器: clang 15.0.4 / clang++
- 链接器: bfd（lld 因 libxml2.so.16 缺失不可用）
- 状态: built

## 编译步骤

1. 源码下载：从 GitHub 下载 1.4.1 tarball（因 SSL 证书问题使用 `curl -kL` 手动下载）
2. 运行 `autoreconf -fi` 生成 configure 脚本（源码仅含 configure.ac）
3. 修补 configure 脚本：跳过 "cannot run C compiled programs" 检测（鸿蒙 ELF 签名导致 conftest 无法执行）
4. 修补 configure 脚本：将 mktemp umask 从 077 改为 007 + chmod g+rwx（HMDFS UID 映射权限问题）
5. 运行 configure：`CONFIG_SHELL=bash bash ./configure --prefix=$DEFAULT_PREFIX LDFLAGS="-fuse-ld=bfd -L$DEFAULT_PREFIX/lib"`
6. 运行 `make -j1`：成功编译 3 个工具（cuebreakpoints, cueconvert, cueprint）+ 1 个脚本（cuetag.sh）
7. 运行 `make install DESTDIR=$TEST_PREFIX`：安装到 staging 目录
8. 运行 `make check`：无测试套件，所有目标返回空
9. 运行 `make install`（不带 DESTDIR）：安装到 $DEFAULT_PREFIX
10. 使用 `ohc-run.py sign-elf` 对 3 个二进制进行 ELF 签名
11. 功能验证：所有工具正常工作
12. 运行 `ohc-run.py package`：打包预编译包
13. 运行 `ohc-run.py verify-build`：G1-G4 全通过
14. 运行 `ohc-run.py clean-verify`：G0 干净构建验证通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败，无法下载源码 | 鸿蒙环境 SSL 证书不完整 | 使用 `curl -kL` 下载后手动放置到 `$HOME/tmp/builds/` |
| 2 | C compiler cannot create executables | lld 链接器依赖 libxml2.so.16 缺失 | 使用 `LDFLAGS="-fuse-ld=bfd"` 替代 lld |
| 3 | configure: cannot run C compiled programs | 鸿蒙 ELF 签名机制，未签名二进制无法执行 conftest | 修改 configure 脚本跳过运行时检测（`if test "$cross_compiling" != yes` → `if false`；添加 `cross_compiling=no`） |
| 4 | config.status: subs1.awk Permission denied | HMDFS 文件系统上 mktemp 创建的 0700 目录被 UID 20001006 拥有，进程 UID 20020082 无法写入 | 修改 configure/config.status 将 umask 从 077 改为 007，并添加 `chmod g+rwx "$tmp"` |
| 5 | 安装后二进制 permission denied | 未签名的 ELF 在鸿蒙上无法执行 | 使用 `ohc-run.py sign-elf` 签名 |

## 真实功能测试结果

### cuebreakpoints 真实 CUE 文件解析
```
输入: 2 轨道的 CUE 文件（Track 01 INDEX 01 00:00:00, Track 02 INDEX 01 02:35:00）
输出: 2:35.00
```
✅ 正确解析了轨道索引时间点

### cueconvert CUE→TOC 格式转换
```
输入: CUE 格式文件
输出: TOC 格式文件（包含 CD_DA, CD_TEXT, TRACK AUDIO 等标记）
```
✅ 成功转换格式，保留了 CD-TEXT 元数据

### cueprint 碟片信息打印
```
输出: performer=Test Artist, title=Test Album, no. of tracks=2
Track 1: performer=Test Artist, title=Track 1
Track 2: performer=Test Artist, title=Track 2
```
✅ 正确解析并打印碟片/轨道信息

### 版本号
```
cuebreakpoints -V → cuetools 1.4.0
cueconvert -V → cuetools 1.4.0
cueprint -V → cuetools 1.4.0
```
注：configure.ac 声明版本为 1.4.0，release tag 为 1.4.1

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| cuetools-1.4.1-ohos-aarch64.tar.gz | 482KB | 预编译包（3 ELF 二进制 + cuetag.sh + 3 man 页） |
| cuetools-1.4.1-ohos-aarch64-debug.tar.gz | 78KB | 调试符号包 |

打包产物内容：
- bin/cuebreakpoints (150KB, ELF签名+strip+RPATH)
- bin/cueconvert (150KB, ELF签名+strip+RPATH)
- bin/cueprint (150KB, ELF签名+strip+RPATH)
- bin/cuetag.sh (4KB, shell script)
- share/man/man1/cuebreakpoints.1, cueconvert.1, cueprint.1

## 注意事项

- 此软件无上游测试套件（`make check` 所有目标为空）
- configure.ac 版本声明为 1.4.0，但 release tag 为 1.4.1
- 所有修改已固化在补丁中：14 个 autoreconf 生成的辅助文件 + 1 个 configure 平台适配补丁
- 仅依赖 libc.so (musl)，无额外库依赖
---

**编译结束**: 2026-06-04 15:05
**最终状态**: built
---

**编译结束**: 2026-06-04 15:06
**最终状态**: built
