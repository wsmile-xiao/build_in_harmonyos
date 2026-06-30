# libcdio 2.3.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-28
- 编译器: clang 15.0.4 / clang++
- 状态: built

## 编译步骤

1. `ohc-run.py init-build libcdio 2.3.0` — 初始化构建环境
2. 下载源码并解压到 `~/tmp/builds/libcdio-2.3.0.work`
3. 运行 `patch-autotools-ohos.pl config.guess config.sub` — 为 OHOS 打补丁
4. 修改 `configure` 脚本中的 umask 077 → umask 022（HMDFS 兼容性）
5. `./configure --prefix=/storage/Users/currentUser/usr/local`
6. 生成 config.status 后，同样修改其 umask 077 → umask 022 + chmod 755
7. 运行 `./config.status` 生成所有 Makefiles
8. `make -j2`
9. `make install DESTDIR=$TEST_PREFIX` — staging 安装
10. staging 验证通过
11. `make check` — 20 PASS, 2 SKIP, 1 XFAIL, 1 FAIL (平台限制)
12. `verify-build` — G1-G4 PASS
13. `ohc-run.py package` — 打包预编译包
14. `make install` — 本地安装（无 DESTDIR）
15. 用户验证通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | E007: GNU config.guess 不含 OHOS 检测 | `patch-autotools-ohos.pl config.guess config.sub` |
| 2 | config.status 创建临时目录后无法写入文件 | HMDFS 上 mktemp -d 配合 umask 077 创建的目录权限为 drwx--S---，HMDFS 拒绝写入 | 修改 configure 和 config.status 中 umask 077 → umask 022，并添加 chmod 755 |
| 3 | check_udf.sh 测试失败 | E002: 测试硬编码 /tmp 为提取目录，OHOS 上 /tmp 为只读 | 平台限制，非软件缺陷 |
| 4 | libcddb 未找到 | 未安装 libcddb 预编译包 | CDDB 功能被禁用，非必需 |
| 5 | ncurses 未找到 | ncurses 未以 pkg-config 可发现方式安装 | cdda-player 被禁用，非必需 |

## 源码修改

| 文件 | 修改内容 |
|------|----------|
| config.guess | OHOS LIBC 检测 + HarmonyOS 系统识别（patch-autotools-ohos.pl） |
| config.sub | ohos-linux 三元组 + linux-ohos 内核（patch-autotools-ohos.pl） |
| configure | umask 077 → umask 022 + chmod 755 $ac_tmp（HMDFS 兼容） |

## 依赖版本

- clang 15.0.4
- GNU Make 4.4.1
- autoconf 2.72 / automake 1.17

## 验证结果

```
$ cd-drive --version → cd-drive version 2.3.0 aarch64-unknown-linux-ohos
$ cd-info --version → cd-info version 2.3.0 aarch64-unknown-linux-ohos
$ iso-info --version → iso-info version 2.3.0 aarch64-unknown-linux-ohos
$ pkg-config --modversion libcdio → 2.3.0
$ pkg-config --modversion libiso9660 → 2.3.0
$ pkg-config --modversion libudf → 2.3.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libcdio-2.3.0-ohos-aarch64.tar.gz | 2.3M | 预编译包（含 bin/lib/include/pkgconfig） |
| libcdio-2.3.0-ohos-aarch64-debug.tar.gz | 954K | 调试符号包 |

## 注意事项

- HMDFS 上 umask 077 + mktemp 创建的目录无法写入文件，需改为 umask 022
- 1 个测试失败（check_udf.sh）是平台限制（/tmp 只读），不影响功能
- CDDB 和 cdda-player 功能因缺少 libcddb/ncurses 而被禁用，对核心库功能无影响
---

**编译结束**: 2026-05-28 10:59
**最终状态**: built
