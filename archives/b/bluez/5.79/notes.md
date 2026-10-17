# bluez 5.79 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-12
- 编译器: clang 15.0.4
- 状态: built（手动编译验证通过，待 conan 固化）

## 编译步骤

```bash
# 依赖（cmd-pkgs 预编译包，R18）
sh install.sh glib 2.88.0
sh install.sh dbus 1.14.10
sh install.sh readline 8.2
sh install.sh pcre2 10.40        # glib 的 pkg-config 依赖
sh install.sh coreutils 9.10     # 提供 install 命令（ginstall -> install 符号链接）

# config.guess/sub 打 OHOS 识别补丁（E007）
perl patch-autotools-ohos.pl config.guess config.sub
# 补 config.sub 内核-OS 组合校验缺 linux-ohos*（patch 脚本 4/5 分，需手动补）

# configure：E011 umask 077 -> 022；禁 OHOS 不可用组件
sed -i 's/umask 077/umask 022/g' configure
./configure --prefix=$DEFAULT_PREFIX --disable-udev --disable-systemd --disable-obex

make -j2
make install DESTDIR=$TEST_PREFIX
make check
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别系统类型 | E007: config.guess/sub 无 HarmonyOS 分支 | patch-autotools-ohos.pl 打补丁 |
| 2 | Kernel linux not known to work with OS ohos | config.sub 内核-OS 组合校验缺 linux-ohos* | 手动在 case $kernel-$os 中补 `linux-ohos*` |
| 3 | config.status: cannot create confXXX/subs1.awk: Permission denied | E011: HMDFS 上 umask 077 && mktemp -d 创建 0700 目录对当前进程不可写 | configure 中 umask 077 -> 022 |
| 4 | gdbus/object.c: MAX_INPUT undeclared | musl/OHOS 无 glibc MAX_INPUT 宏 | 仿 src/shared/util.c 加 `#ifndef MAX_INPUT #define MAX_INPUT _POSIX_MAX_INPUT` |
| 5 | undefined symbol g_libintl_* (btmon 等链接失败) | libglib-2.0.a 引用 g_libintl_* 符号，仅静态 libintl.a 提供；libtool 会重组 -Wl,-Bstatic 导致失效 | GLIB_LIBS 中用完整路径 `/…/usr/local/lib/libintl.a` 引用 |
| 6 | tools/obexctl.c: undefined symbol rindex | rindex 为 BSD 遗留函数，OHOS musl libc 无此符号 | 5 处 rindex() -> strrchr() |
| 7 | make install: install: No such file or directory | OHOS 无 coreutils install 命令 | 安装 coreutils 9.10，建 ginstall -> install 符号链接 |
| 8 | test-sdp 链接失败: __start___debug/__stop___debug undefined | lld 15 --gc-sections 会裁掉 __start_/__stop_ 封装符号 | MISC_LDFLAGS 追加 `-Wl,-z,nostart-stop-gc` |
| 9 | unit/test-textfile: /tmp/textfile 删除断言失败 | E002: /tmp 只读，测试硬编码 /tmp 路径 | 测试改用 TMPDIR 环境变量（main 中 snprintf 填充） |
| 10 | unit/test-avdtp: setsockopt(SO_PRIORITY) Operation not permitted | OHOS 沙箱无 CAP_NET_ADMIN，SO_PRIORITY 返回 EPERM 且被当作致命错误 | android/avdtp.c set_priority: EPERM/EACCES 视为尽力而为不失败 |
| 11 | unit/test-vcp 间歇失败（整批运行时） | 测试框架 GATT 通知时序竞态（单独运行 20/20 通过；批次运行偶发 5==7 字节断言失败），非平台适配缺陷 | 记录为已知 flaky，不阻塞 |

## 源码修改

探索阶段源码修改（finish 时 refresh-patch --auto 生成 patches/）：
- `config.guess` — HarmonyOS 识别分支（patch-autotools-ohos.pl）
- `config.sub` — ohos-linux 三元组 + OS 列表 + 内核-OS 组合校验（补 linux-ohos*）
- `configure` — umask 077 -> 022（E011）
- `gdbus/object.c` — MAX_INPUT musl 兼容定义
- `Makefile` — GLIB_LIBS 用完整路径引用 libintl.a；MISC_LDFLAGS 加 -z nostart-stop-gc
- `tools/obexctl.c` — rindex() -> strrchr() ×5
- `unit/test-textfile.c` — /tmp 硬编码路径改为 TMPDIR 环境变量
- `android/avdtp.c` — set_priority 对 EPERM/EACCES 不致命

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| glib | 2.88.0 | cmd-pkgs 预编译包（制品仓 glib/2.84.0.1 将用于 conan 配方） |
| dbus | 1.14.10 | cmd-pkgs 预编译包（制品仓已发布） |
| readline | 8.2 | cmd-pkgs 预编译包（制品仓 readline/8.3 已发布） |
| pcre2 | 10.40 | cmd-pkgs 预编译包 |
| coreutils | 9.10 | cmd-pkgs 预编译包（install 命令） |

## 验证结果

```bash
make check: 25 测试，24 PASS，1 FAIL（test-vcp 时序 flaky，单独运行通过）
staging 冒烟: bluetoothctl/btmon/btattach/hex2hcd --version 均输出 5.79
```

## 注意事项

- `--disable-udev --disable-systemd --disable-obex`：OHOS 无 systemd/udev；libical（OBEX 依赖）未发布制品仓，OBEX 为可选 profile，禁用不影响核心蓝牙栈
- ell 使用 bluez 内置版本（不启用 --enable-external-ell），无需外部 ell 依赖
- conan 配方中 glib 依赖用制品仓 glib/2.84.0.1（含 OHOS binary）
---

**编译结束**: 2026-08-13 00:16
**最终状态**: published
