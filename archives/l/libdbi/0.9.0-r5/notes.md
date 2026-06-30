# libdbi 0.9.0-r5 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-02
- 编译器: clang 15.0.4
- 状态: published

## 编译步骤

1. 初始化: `python3 $SKILL_ROOT/scripts/ohc-run.py init-build libdbi 0.9.0-r5 --no-download`
   - 源码来自 SourceForge (libdbi-0.9.0.tar.gz)，因 Savannah URL 404 和 SSL 证书问题，手动下载后使用 --no-download
2. 替换 config.guess/config.sub: 用 automake-1.16 的新版本替换 2003 年的旧版本以识别 HarmonyOS
3. 修复 configure/config.status 的 umask 077 → umask 022（HMDFS setgid 行为导致权限问题）
4. configure: `./configure --prefix=$DEFAULT_PREFIX` (CONFIG_SHELL=bash)
5. make -j1: 编译成功
6. make install DESTDIR=$TEST_PREFIX: staging 安装成功
7. make check: 无测试套件，通过
8. package: 打包成功
9. make install (不带 DESTDIR): 本地安装成功
10. 验证: pkg-config --modversion dbi → 0.9.0

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 旧版 config.guess (2003-07-02) 不支持 HarmonyOS/aarch64 | 替换为 automake-1.16 的 config.guess/config.sub |
| 2 | configure/config.status 创建临时目录后写入文件 Permission denied | HMDFS 文件系统 setgid 行为：umask 077 创建的 drwx--S--- 目录，即使 owner 也无法写入 | 将 configure/config.status 中 umask 077 改为 umask 022 |
| 3 | Savannah 下载 URL 404 | libdbi-0.9.0-r5 是 Alpine 版本号，upstream tarball 是 libdbi-0.9.0.tar.gz | 使用 SourceForge URL 手动下载 |

## 源码修改

### 替换文件（非补丁形式）
- config.guess: 替换为 automake-1.16 版本（支持 aarch64-unknown-linux-ohos）
- config.sub: 替换为 automake-1.16 版本
- configure: umask 077 → umask 022（第 13574/13579 行）
- config.status: umask 077 → umask 022（第 792/797 行）

## 依赖版本

无外部依赖（纯 C 库，仅需 libc）

## 验证结果

```bash
$ PKG_CONFIG_PATH=$HOME/usr/local/lib/pkgconfig pkg-config --modversion dbi
0.9.0
$ ls $HOME/usr/local/lib/libdbi.so*
libdbi.so  libdbi.so.1  libdbi.so.1.1.0
$ ls $HOME/usr/local/include/dbi/
dbd.h  dbi-dev.h  dbi.h
```

## 功能测试结果

### API 功能测试（2026-06-02）

| 测试项 | 结果 | 详情 |
|--------|------|------|
| dbi_version() | ✅ | 返回 "libdbi v0.9.0" |
| dbi_version_numeric() | ✅ | 返回 900 |
| dbi_initialize_r(NULL, &inst) | ⚠️ | 返回 -1（默认驱动目录不存在） |
| dbi_conn_new_r (无驱动) | ✅ | 无驱动时正确返回 NULL |
| dbi_set_verbosity_r | ✅ | 正常 |
| dbi_shutdown_r | ✅ | 正常（需先 initialize） |
| 编译链接 | ✅ | 所有公共 API 可编译链接 |
| ELF 签名 | ✅ | .note.ohos.ident + .codesign 完整 |
| pkg-config | ✅ | --modversion/--cflags/--libs 正常 |

### 结论
- 核心库 API 在鸿蒙平台功能正常
- dbi_initialize_r 需指定驱动目录路径（默认路径 /usr/lib/dbd/ 不存在）
- 建议安装 libdbi-drivers 后重新验证完整功能

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libdbi-0.9.0-r5-ohos-aarch64.tar.gz | 2298KB | 预编译包 |

## 注意事项

- HMDFS 上 umask 077 创建的目录无法写入（setgid 继承导致 owner 也被拒），这是平台级问题（E002/E046 相关）
- libdbi 是纯库软件，没有可执行二进制文件，验证需用 pkg-config 而非 --version
- ldconfig 不可用，但不影响功能

---
**编译结束**: 2026-06-02
**最终状态**: published
