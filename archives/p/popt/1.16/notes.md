# popt 1.16 — 编译进度

> 档案创建时间: 2026-04-25
> 最后更新: 2026-07-26 (v8.7 Conan 迁移)
> 当前状态: conan create ✅ | test_package 1/1 ✅

## v8.7 Conan 迁移 (2026-07-26)

- conanfile.py: Autotools + E007 补丁 + E097 umask 修复
- conandata.yml: http://ftp.rpm.org/mirror/popt/popt-1.16.tar.gz
- test_package: CMake + test_popt.c (popt API 命令行解析)
- conan create 验证通过: configure → make → install → test_package 1/1 ✅
- E097 新增: autoconf umask 077 在 HMDFS setgid 下导致 config.status 权限错误

## 旧版记录 (v7.8, 2026-04-25 ~ 2026-06-04)

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | popt |
| 版本 | 1.16 |
| 状态 | ✅ built |
| 构建系统 | autotools |
| 下载源 | http://ftp.rpm.org/mirror/popt/popt-1.16.tar.gz |
| 平台 | aarch64-unknown-linux-ohos |

## 二、编译步骤

### Phase 1: 环境准备
- [x] ohc-run.py init-build popt 1.16 --url=http://ftp.rpm.org/mirror/popt/popt-1.16.tar.gz
- [x] 源码下载解压完成

### Phase 2: 编译
- [x] E007 修复：替换 config.guess/config.sub 为 automake-1.16 版本 (2023-08-22/2023-09-19)
- [x] configure --prefix=$DEFAULT_PREFIX 成功 (检测平台 aarch64-unknown-linux-ohos)
- [x] make -j2 成功 (仅有编译警告，无错误)
- [x] make install DESTDIR=$TEST_PREFIX staging 安装成功

### Phase 3: 测试验证
- [x] make check: 57/58 通过
- [ ] 1/58 失败: test58 (libtool lt-test1 vs test1 命名匹配问题，非功能性缺陷)
- [x] verify-build 质量门禁 PASS

### Phase 4: 预编译包制作
- [x] ohc-run.py package popt 1.16 完成
- [x] popt-1.16-ohos-aarch64.tar.gz (1215KB)
- [x] ELF签名完成

### Phase 5: 本地安装验证
- [x] make install (无 DESTDIR) → ~/usr/local
- [x] pkg-config --modversion popt = 1.16 ✅
- [x] libpopt.so.0.0.0 + libpopt.a 安装到 ~/usr/local/lib
- [x] popt.h 安装到 ~/usr/local/include

## 三、编译问题记录

### E007: config.guess/config.sub 不识别 HarmonyOS
- **原因**: popt 1.16 源码包含 2009 年版本的 config.guess/config.sub
- **修复**: 替换为 automake-1.16 (2023版) 的文件，内含 HarmonyOS 支持
- **验证**: ./config.guess 输出 `aarch64-unknown-linux-ohos` ✅

### make check test58 失败
- **原因**: libtool wrapper 命名差异 — 测试期望 `lt-test1`，实际输出 `test1`
- **影响**: 仅影响 usage 输出中的程序名，不影响库功能
- **分类**: popt 测试套件的已知问题，非平台适配问题

## 四、源码修改清单

| 文件 | 原因 | 方式 |
|------|------|------|
| config.guess | E007: 不识别 HarmonyOS | 替换为 automake-1.16 版本 |
| config.sub | E007: 不识别 aarch64-HarmonyOS | 替换为 automake-1.16 版本 |

## 五、安装产物

| 文件 | 路径 | 说明 |
|------|------|------|
| libpopt.so.0.0.0 | ~/usr/local/lib | 共享库 (59840 bytes) |
| libpopt.so.0 → libpopt.so.0.0.0 | ~/usr/local/lib | 符号链接 |
| libpopt.so → libpopt.so.0.0.0 | ~/usr/local/lib | 符号链接 |
| libpopt.a | ~/usr/local/lib | 静态库 (56222 bytes) |
| popt.h | ~/usr/local/include | 头文件 |
| popt.pc | ~/usr/local/lib/pkgconfig | pkg-config 元数据 |
| popt.3 | ~/usr/local/share/man/man3 | man page |

## 六、后续编译依赖

popt 编译成功，可作为 libgphoto2 和 gphoto2 的编译基础。
使用 `pkg-config --cflags popt` 和 `pkg-config --libs popt` 获取编译参数。---

**编译结束**: 2026-06-04 01:55
**最终状态**: built
---

**编译结束**: 2026-06-04 02:05
**最终状态**: built
