# avahi-ui-tools 0.8 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-01
- 编译器: clang/clang++ (LLVM 15.0.4, aarch64-linux-ohos)
- 状态: built

## 编译步骤

avahi-ui-tools 不是独立源码项目，而是上游 avahi 源码树（GitHub tag v0.8）中
`avahi-ui/` 子目录的 GUI 工具分包（bin_PROGRAMS=bssh，安装时由
install-exec-local 生成 bvnc/bshell 符号链接）。本配方构建
`avahi-common → avahi-client → avahi-glib → avahi-ui` 四个子目录
（与同源 avahi-ui/0.8 库配方同一构建链），但包类型为 application：
只发布 bssh/bvnc/bshell 可执行文件，不发布任何库。

GitHub tag 归档无生成后的 configure 脚本，配方在 build() 中先执行 autogen.sh
（NOCONFIGURE=1 防止其自行运行 configure），生成 configure 后手动运行：

```
NOCONFIGURE=1 CONFIG_SHELL=$SHELL SHELL=$SHELL ./autogen.sh
./configure --prefix=<pkg> --enable-glib --enable-gtk3 --enable-tests \
    --disable-gtk --disable-nls --disable-introspection \
    --disable-compat-libdns_sd --disable-compat-howl --disable-libevent \
    --disable-qt3 --disable-qt4 --disable-qt5 --disable-python --disable-mono \
    --disable-autoipd --disable-core-docs --disable-manpages --disable-xmltoman \
    --disable-gdbm --disable-libdaemon
make -C avahi-common
make -C avahi-client
make -C avahi-glib
make -C avahi-ui
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | autogen.sh 无法直接执行 | 签名 `#!/bin/bash`，HMFS 无 /bin/bash | 用 `sh autogen.sh` 显式解释执行（CONFIG_SHELL/SHELL 同步） |
| 2 | 运行时动态库缺 libc++_shared.so | GTK 栈含 C++ 产物（harfbuzz） | test_package 使用 VirtualRunEnv，运行环境追加 /system/lib64 |

> 其余平台适配（configure AS_TMPDIR umask、autogen 工具链 staging、
> GLib SO 绝对路径固定、HMFS 符号链接约束）与同源 avahi-ui/0.8 配方
> 完全一致，此为从库配方继承的已验证逻辑（该配方 conan-verify 全过）。

## 源码修改

无（未修改上游源码，未打补丁）。

## 依赖版本

- gtk/3.24.43
- glib/2.84.0.1
- dbus/1.14.10
- expat/2.8.2.1 (override)
- automake/1.18 (tool)
- libtool/2.5.4 (tool)
- gettext/0.22.5.1 (tool)

## 验证结果

- `conan create .` 通过：bssh 二进制与 bvnc/bshell 别名构建并打包成功
- 上游单元测试 6 项（avahi-common: strlst/domain/alternative/timeval/utf8；
  avahi-glib: glib-watch）全部通过
- test_package 5 项 CLI 契约断言（三二进制存在性/可执行位/未知选项拒绝路径）
  全部通过
- conan-verify 门禁 G0-G4 + L2/L4/L5 全部通过

## 注意

- bssh 为 GTK3 图形前端（需要交互式会话 + 运行中的 avahi-daemon），
  消费端测试仅覆盖 offline CLI 契约（未知选项拒绝发生在 gtk_init 之前，
  headless 安全），GUI 渲染路径建议合入后在真机确认（与 avahi-ui 同口径）
- 本包与 avahi-ui/0.8 库包同源同链，若后续 avahi-ui 库配方有平台修复，
  本配方构建链需同步比对

**编译结束**: 2026-09-01
**最终状态**: built（conan-verify G0-G4 + L2/L4/L5 全过，待合入后 CI 发布）
**结束标记**: COMPLETED
---

**编译结束**: 2026-09-01 21:24
**最终状态**: built
