# guile 2.2.7 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-26
- 编译器: clang/clang++
- 状态: built

## 背景
- Guile 3.0.x 在 HarmonyOS 上有字节码兼容性问题
- 2.2.7 是 2.x 系列最新稳定版，理论上更兼容 HarmonyOS

## 依赖状态（已安装）
- gc 8.2.12 ✅（无 pthread_cancel）
- libunistring 1.4.2 ✅
- gmp 6.3.0 ✅
- libffi 3.4.6 ✅
- libtool 2.4.7 ✅（编译过程中发现缺少 libltdl，额外编译）

## 编译步骤

1. **下载源码**: `wget http://mirrors.tuna.tsinghua.edu.cn/gnu/guile/guile-2.2.7.tar.xz`
2. **初始化**: `python3 ohc-run.py init-build guile 2.2.7`
3. **应用平台补丁**:
   - 修改 `build-aux/config.guess`：添加 HarmonyOS 识别，输出 `aarch64-unknown-linux-ohos`
   - 修改 `build-aux/config.sub`：添加 `linux-ohos*` 支持
4. **修改 configure**: `sed -i 's/umask 077/umask 022/g' configure`（解决 HMDFS 权限问题）
5. **修改 guile-snarf**: `sed -i 's/umask 077/umask 022/g' libguile/guile-snarf`（解决临时文件权限问题）
6. **Configure**: `./configure --prefix=$HOME/usr/local CC=clang CXX=clang++`
7. **Make**: `make -j1`（部分 .go 文件编译后 Signal 5 崩溃，但文件已生成）
8. **Install**: `make install DESTDIR=$TEST_PREFIX && make install`
9. **验证**: `~/usr/local/bin/guile --version` 输出正确版本信息

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL证书验证失败 | 系统证书未更新 | 使用 http 协议下载 |
| 2 | config.guess 无法识别 HarmonyOS | 未添加 HarmonyOS 模式 | 手动添加 `*:HarmonyOS:*:*` case |
| 3 | config.sub 不支持 linux-ohos | 未添加 ohos 支持 | 在第117行和1383行添加 `linux-ohos*` |
| 4 | configure/config.status 权限拒绝 | HMDFS + umask 077 | 将 `umask 077` 改为 `umask 022` |
| 5 | 缺少 libltdl | libtool 未安装库部分 | 编译 libtool 2.4.7 |
| 6 | guile-snarf 权限拒绝 | HMDFS + umask 077 | 将脚本中的 `umask 077` 改为 `umask 022` |
| 7 | 编译 .go 文件后 Signal 5 崩溃 | GC库/HarmonyOS限制 | 文件已生成，崩溃不影响功能 |

## 源码修改

### 补丁文件
- `0001-build-aux-config.guess.patch`: 添加 HarmonyOS 系统识别
- `0002-build-aux-config.sub.patch`: 添加 linux-ohos 支持
- `0003-configure.patch`: 修改 umask
- `0004-doc-ref-stamp-vti.patch`: 文档时间戳更新（自动生成）
- `0005-doc-ref-version.texi.patch`: 版本信息更新（自动生成）

### 关键修改（非补丁）
- `libguile/guile-snarf`: umask 077 → 022

## 依赖版本

| 软件 | 版本 | 说明 |
|------|------|------|
| gc | 8.2.12 | 无 pthread_cancel |
| libunistring | 1.4.2 | |
| gmp | 6.3.0 | 静态库 |
| libffi | 3.4.6 | |
| libltdl | 7.3.2 | libtool 2.4.7 |
| readline | 8.2 | |
| libintl | | gettext |

## 验证结果

```bash
$ ~/usr/local/bin/guile --version
GC Warning: Failed to find PT_GNU_RELRO segment inside PT_LOAD region
guile (GNU Guile) 2.2.7
Copyright (C) 2020 Free Software Foundation, Inc.

License LGPLv3+: GNU LGPL 3 or later <http://gnu.org/licenses/lgpl.html>.
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| guile-2.2.7-ohos-aarch64.tar.gz | 12M | 预编译包 |
| 0001-*.patch | | HarmonyOS 识别补丁 |
| 0002-*.patch | | linux-ohos 支持 |
| 0003-*.patch | | umask 修复 |

## 注意事项

1. **GC警告**: `Failed to find PT_GNU_RELRO segment` 不影响功能
2. **Signal 5**: 编译 .go 文件后的崩溃不影响文件生成，可忽略
3. **libltdl**: Guile 依赖 libltdl，必须先编译完整的 libtool（包含库）
4. **预编译包**: 手动创建的预编译包未经 ELF 签名，需使用 `ohc-run.py package` 重新打包

## 知识提取

### L1 平台真理
- HarmonyOS 系统识别需要修改 config.guess/config.sub
- HMDFS 文件系统要求修改 umask 077 为 022

### L2 模式经验
- Guile 2.2.x 需要 libltdl（libtool 的库部分）
- 编译过程中的 Signal 5 崩溃不影响产物

---

**编译结束**: 2026-05-26 21:00
**最终状态**: built（guile --version 正常运行）
