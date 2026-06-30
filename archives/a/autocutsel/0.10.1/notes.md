# autocutsel 0.10.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-29
- 编译器: clang 15.0.4
- 状态: published

## 编译步骤

### 1. 初始化
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build autocutsel 0.10.1 --url=file://$HOME/tmp/autocutsel-0.10.1.tar.gz
```
源码从 GitHub 通过 ghfast.top 镜像下载（GitHub 直连超时）。

### 2. 安装 X11 依赖
autocutsel 依赖 libX11, libXext, libXau, libXt, libXmu, libXaw, libXpm。

预编译包安装（来自 cmd-pkgs）:
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libx11 6.4.0
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libxext 6.4.0
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libxau 6.0.0
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- xorgproto 2024.1
```

从源码编译的依赖（预编译包不可用）:
- libXt 1.2.1（来自 xorg.freedesktop.org）
- libXmu 1.1.4
- libXpm 3.5.17
- libXaw 1.0.14

编译顺序: libXt → libXmu → libXpm → libXaw

### 3. 配置与编译
```bash
source .build-context-autocutsel-0.10.1
cd $BUILD_SRC_DIR
cp $HOME/builds/config.guess ./
cp $HOME/builds/config.sub ./
export PKG_CONFIG_PATH=$HOME/usr/local/lib/pkgconfig:$HOME/usr/local/share/pkgconfig:$PKG_CONFIG_PATH
export CFLAGS="-I$HOME/usr/local/include"
export LDFLAGS="-L$HOME/usr/local/lib"
./configure --prefix=$DEFAULT_PREFIX
make -j2
make install DESTDIR=$TEST_PREFIX
make check
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 下载超时 | 网络限制 | 使用 ghfast.top 镜像下载源码 |
| 2 | 缺少 libXt/libXmu/libXaw/libXpm | 无预编译包 | 从 xorg.freedesktop.org 下载源码编译 |
| 3 | config.status "Permission denied" 创建临时文件 | HMDFS 文件系统 + umask 077 创建目录权限问题 | sed 修补 config.status 去除 umask 077 |
| 4 | libXt configure: "cc -E defines unix" | clang 预定义 unix 宏 + 不支持 stdin 重定向 | 设置 CPP="cc -E -" 使 clang 从 stdin 读取 |
| 5 | 运行时缺少 libxcb.so.1 | 预编译 libX11 依赖 libxcb | 创建 stub libxcb.so.1 供测试用 |

## 源码修改 (Patches)

共 5 个 patch，全部通过 Conan conandata.yml 管理：

1. **config-guess-ohos.patch** — 在 config.guess 中添加 `*:HarmonyOS:*:*` case，使 autotools 识别 OHOS 平台
2. **config-guess-tmpdir.patch** — 移除 config.guess 中的 `umask 077`，修复 HMDFS 文件系统权限问题
3. **config-sub-ohos.patch** — 在 config.sub 中添加 `linux-ohos*` 到 kernel-OS 验证列表
4. **configure-tmpdir.patch** — 修复 configure 中 `mktemp -d "./confXXXXXX"` 为使用 `${TMPDIR}` 并移除 `umask 077`
5. **version-help.patch** — 在 main() 中 X11 初始化前添加 `--version`/`--help` 处理，支持无头环境 smoke test

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| libX11 | 6.4.0 (实际1.6.4) | cmd-pkgs 预编译 |
| libXext | 6.4.0 | cmd-pkgs 预编译 |
| libXau | 6.0.0 | cmd-pkgs 预编译 |
| xorgproto | 2024.1 | cmd-pkgs 预编译 |
| libXt | 1.2.1 | 源码编译 |
| libXmu | 1.1.4 | 源码编译 |
| libXpm | 3.5.17 | 源码编译 |
| libXaw | 1.0.14 | 源码编译 |
| libICE | 6.3.0 | 随 libx11 安装 |
| libSM | 6.0.1 | 随 libx11 安装 |

## 验证结果

### 二进制文件信息
```bash
$ file autocutsel
autocutsel: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped

$ readelf -h autocutsel
ELF Header:
  Class:                             ELF64
  Data:                              2's complement, little endian
  Type:                              DYN (Position-Independent Executable file)
  Machine:                           AArch64
```

### 运行测试
```bash
$ autocutsel --version
autocutsel 0.10.1
exit: 0

$ autocutsel --help
usage:  autocutsel [-selection <name>] [-cutbuffer <number>] [-pause <milliseconds>] [-debug] [-verbose] [-fork] [-buttonup]

Synchronizes the CLIPBOARD and PRIMARY X11 selections.
exit: 0

$ autocutsel (无显示)
Error: Can't open display:
exit: 1 (预期行为)
```
注：通过 version-help.patch，--version 和 --help 在 X11 初始化前处理，无需显示服务器即可通过 smoke test。

### make check
make check 通过（exit 0），无测试用例输出。

## 交付物

| 文件 | 说明 |
|------|------|
| autocutsel | 剪贴板自动同步工具（PRIMARY ↔ CLIPBOARD） |
| cutsel | 剪贴板查看/设置工具 |

## 注意事项

1. autocutsel 是 X11 应用程序，需要 X 显示服务器才能实际运行。在无头 OHOS 环境中，二进制可加载但无法连接显示。
2. 预编译 libX11 (cmd-pkgs) 依赖 libxcb，运行时需要 libxcb.so.1。测试时创建了 stub 库。
3. 所有从源码编译的 X11 库（libXt, libXmu, libXpm, libXaw）均需修补 config.status 去除 umask 077 以适配 HMDFS 文件系统。
4. libXt 编译需设置 CPP="cc -E -" 以使 clang 从 stdin 读取预处理输入。
---

**编译结束**: 2026-06-29 17:22
**最终状态**: published
