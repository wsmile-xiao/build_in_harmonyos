# nbd 3.26.1 适配笔记

## 编译环境
- 构建系统: autotools (configure.ac + Makefile.am + autogen.sh)
- 编译日期: 2026-08-07
- 编译器: clang/clang++ (HNP 15.0.4)
- 状态: built

## 编译步骤

```bash
# 1. 安装构建工具 (via Harmonybrew)
brew install automake libtool autoconf-archive

# 2. 安装依赖 (via conan ohpcd remote)
conan install --requires=glib/2.84.0 -r=ohpcd -g=PkgConfigDeps -g=AutotoolsDeps -g=AutotoolsToolchain

# 3. 生成 configure
ACLOCAL_PATH="/data/service/hnp/pkg-config.org/pkg-config_0.29.2/share/aclocal:$(brew --prefix autoconf-archive)/share/aclocal" autoreconf -fi

# 4. 配置
./configure --build=aarch64-linux-ohos --host=aarch64-linux-ohos \
  --prefix=$HOME/usr/local --without-gnutls --with-libnl --disable-manpages

# 5. 编译
make -j1

# 6. 安装
make install DESTDIR=$HOME/tmp/stage-nbd

# 7. 测试
make check
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 系统类型不在 config.guess 数据库中 | 显式传递 --build=aarch64-linux-ohos --host=aarch64-linux-ohos |
| 2 | --disable-manpages 报错 "don't know what to do here" | configure.ac 中 AS_IF 逻辑缺少 enable_manpages=no 的分支 | 补充 `[test "x$enable_manpages" = "xno"], []` 分支 |
| 3 | sockaddr_storage 重定义 | linux/socket.h (via libnl3) 和 sys/socket.h 都定义了该结构体 | 在 nbd-client.c 中 `#ifdef __OHOS__` 守卫，定义 `_UAPI_LINUX_SOCKET_H` 跳过 linux/socket.h，同时提供 `__kernel_sa_family_t` typedef |
| 4 | config.status 创建临时目录失败 | mktemp -d 使用 umask 077，在 HarmonyOS HMDFS 上权限不足 | 修改 config.status 中 umask 077 → umask 022 |
| 5 | gthread-2.0.pc 不存在 | glib >= 2.32 将 gthread 合并到 glib，conan 包不提供单独的 .pc | 在 conanfile.py generate() 中创建 gthread-2.0.pc 包装器 |
| 6 | libtool .la 文件路径错误 | conan 包的 .la 文件内嵌路径不匹配 | 删除 conan 包中的 .la 文件，使用 -l 标志直接链接 |
| 7 | AX_PROG_BISON 宏缺失 | 需要 autoconf-archive 包 | 将 ax_prog_bison.m4 作为补丁添加到 support/ 目录 |

## 源码修改

- `patches/0001-configure-ac-fix-manpages-disable.patch`: 修复 configure.ac 中 --disable-manpages 逻辑
- `patches/0002-nbd-client-fix-sockaddr-storage-ohos.patch`: 在 nbd-client.c 中添加 __OHOS__ 守卫解决 sockaddr_storage 重定义
- `patches/0003-add-ax-prog-bison-m4.patch`: 添加 ax_prog_bison.m4 宏文件到 support/ 目录

## 依赖版本

- glib/2.84.0 (conan ohpcd)
- libnl/3.7.0 (conan ohpcd)
- automake/1.18 (conan ohpcd tool_requires)
- libtool/2.5.4 (conan ohpcd tool_requires)
- bison/3.8.2 (conan ohpcd tool_requires)
- flex/2.6.4 (conan ohpcd tool_requires)
- m4/1.4.19 (conan ohpcd tool_requires)
- gnutls: 未在 ohpcd 仓中，使用 --without-gnutls 禁用

## 验证结果

```
nbd-server --version → This is nbd-server version 0.unknown
make check → 12/17 tests passed, 5 failed (all due to /tmp read-only)
```

## 注意事项

- gnutls 未在 ohpcd 制品仓中，当前使用 --without-gnutls 禁用 TLS 支持。
  待 gnutls 适配发布后可通过 conan recipe 的 requirements() 启用。
- make check 中 5 个失败的测试均因 HarmonyOS /tmp 只读导致，非代码问题。
- 源码版本号显示为 "0.unknown" 因为 genver.sh 依赖 git 信息，tarball 源码无 git。
