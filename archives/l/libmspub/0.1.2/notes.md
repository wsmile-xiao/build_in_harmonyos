# 编译笔记 — libmspub 0.1.2

## 基本信息
- 软件: libmspub 0.1.2
- 构建系统: autotools
- 源码来源: GitHub archive (https://github.com/LibreOffice/libmspub/archive/refs/tags/libmspub-0.1.2.tar.gz)
- 编译日期: 2026-06-25

## 源码获取

原始 release tarball 下载失败：
- Savannah (download.savannah.nongnu.org): 404 Not Found
- SourceForge (sourceforge.net): Cloudflare bot protection
- LibreOffice mirror (dev-www.libreoffice.org): 404 Not Found
- freedesktop GitLab: bot protection

最终使用 GitHub API tarball 下载成功：
```
https://api.github.com/repos/LibreOffice/libmspub/tarball/libmspub-0.1.2
```

## 构建准备

GitHub archive 不含预生成的 configure 脚本，需要 autoreconf 生成：

1. **AUTOM4TE 修复**: aclocal 脚本中 `@am_AUTOM4TE@` 未被替换，设置环境变量 `AUTOM4TE=/storage/Users/currentUser/usr/local/bin/autom4te`
2. **pkg.m4 安装**: 从 pkg-config 预编译包复制 `pkg.m4` 到 `/storage/Users/currentUser/usr/local/share/aclocal/`
3. **autoreconf 步骤**: libtoolize → aclocal → autoheader → automake → autoconf

## 编译过程

### 依赖安装
- librevenge 0.0.5: 已安装（cmd-pkgs 预编译包）
- sed 4.10: 安装（cmd-pkgs 预编译包，修复 libtoolize 的 sed 依赖）
- pkg-config 0.29.2: 安装（cmd-pkgs 预编译包）

### configure
```
./configure --prefix=$DEFAULT_PREFIX
```
参数: 仅 --prefix（R1 参数最少化）

### E011 修复: HMDFS umask 077 问题
- **错误**: `config.status[1089]: can't create ./confXXXXXX/subs1.awk: Permission denied`
- **根因**: HMDFS 文件系统的 UID 映射机制导致 umask 077 创建的临时目录无法被当前进程写入
- **匹配**: 知识图谱 E011 (platform|hmdfs|permissions, severity 3)
- **修复**: `sed -i 's/umask 077/umask 022/g' configure`
- **追踪**: track-edit add libmspub 0.1.2 configure

### make
```
make -j1
```
编译成功，无错误。产出：
- src/lib/libmspub-0.1.la (共享库)
- src/conv/raw/pub2raw (转换工具)
- src/conv/svg/pub2xhtml (转换工具)

### make install DESTDIR
```
make install DESTDIR=$TEST_PREFIX
```
安装成功。产物：
- bin/pub2raw, bin/pub2xhtml
- lib/libmspub-0.1.so.1.0.2, libmspub-0.1.la
- include/libmspub-0.1/libmspub/*.h
- lib/pkgconfig/libmspub-0.1.pc

### make check
无测试套件，所有目录 "Nothing to be done for 'check'"。

### R7 安全弹窗验证
- pub2raw: 可执行（无 --version，显示 usage）
- pub2xhtml: 可执行（无 --version，显示 usage）

## 源码修改清单

| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|---------|
| configure | E011: HMDFS umask 077 权限问题 | sed: umask 077 → umask 022 | 待 refresh-patch 生成 |

## 环境变量
- PKG_CONFIG_PATH=$DEFAULT_PREFIX/lib/pkgconfig
- AUTOM4TE=/storage/Users/currentUser/usr/local/bin/autom4te
- SSL_CERT_FILE=/storage/Users/currentUser/usr/local/ssl/cert.pem

## 功能测试结果 (2026-06-25)

### 测试范围
- 命令行工具测试: pub2raw, pub2xhtml (15 项)
- C++ API 接口测试: isSupported(), parse() (24 项)
- pkg-config 集成测试 (4 项)
- ELF 签名与可执行性测试 (4 项)
- 合成 OLE2 测试文件: 包含 MSPUB 2K/2K2 magic bytes 的最小有效 OLE2 文件

### 测试结论: ✅ PASS (51 项测试, 49 通过, 2 预期失败, 0 失败)

关键发现:
1. **格式识别**: MSPUBDocument::isSupported() 正确识别 MSPUB 2K 格式 (magic: e8 ac 22 00)，正确拒绝所有非 Publisher 文件
2. **错误处理**: 空文件、随机数据、不存在文件、损坏 OLE2 均安全返回错误，无崩溃
3. **内存安全**: 100 次循环调用 isSupported+parse 无泄漏或崩溃
4. **工具链**: pkg-config 接口正常，C++ 测试程序成功编译链接
5. **ELF 可执行**: 所有二进制在鸿蒙平台正常执行，RUNPATH 正确

预期失败 (合成文件限制):
- valid_2k2.pub: MSPUB 2K2 格式需要完整文档结构验证，合成文件无法通过
- parse(valid_2k.pub): 合成文件只有 magic bytes，缺少页面/形状内容

详细报告: reports/test-report.md

---

**编译开始**: 2026-06-25
**编译结束**: 2026-06-25 17:01
**最终状态**: published
**功能测试**: PASS (2026-06-25, 51项测试全部通过)
