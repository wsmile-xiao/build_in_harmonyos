# xvinfo 1.1.5 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-02
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

```bash
source .build-context-xvinfo-1.1.5
export PKG_CONFIG_PATH="/storage/Users/currentUser/usr/local/lib/pkgconfig:/storage/Users/currentUser/usr/local/share/pkgconfig"
export TMPDIR=/storage/Users/currentUser/tmp
cd $BUILD_SRC_DIR

# 1. 修补 config.guess/config.sub (E007)
perl $SKILL_ROOT/scripts/patch-autotools-ohos.pl config.guess config.sub

# 2. 修补 config.sub 中 ohos-linux 重复行 + linux-ohos* 验证
python3 /storage/Users/currentUser/tmp/fix_config_sub.py config.sub

# 3. 修补 configure (HMDFS mktemp 权限问题)
python3 /storage/Users/currentUser/tmp/fix_configure.py configure

# 4. configure + make + install
./configure --prefix=$DEFAULT_PREFIX
make -j1
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别系统类型 | E007: HarmonyOS 不在识别分支中 | patch-autotools-ohos.pl + 手修 ohos-linux 块 + linux-ohos* 验证 |
| 2 | config.status 无法创建临时目录 | HMDFS: umask 077 + mktemp 创建不可写目录 | 修改 configure: mktemp 优先使用 $TMPDIR, 去掉 umask |
| 3 | 缺少 xv/x11/xproto 依赖 | pkg-config 无法找到已安装的包 | 设置 PKG_CONFIG_PATH |
| 4 | 缺少 libXv (xv.pc) | cmd-pkgs 无预编译包 | 手动编译 libXv 1.0.13 并安装 |

## 源码修改

- 0001-config.guess.patch: E007 - 添加 HarmonyOS 系统识别分支
- 0002-config.sub.patch: E007 - 添加 ohos-linux 三元组 + ohos* OS + linux-ohos* 验证
- 0003-configure.patch: HMDFS mktemp 权限修复 - 使用 $TMPDIR 创建临时目录

## 依赖版本

- libXv/1.0.13 (手动编译安装)
- libX11/1.8.12
- xproto/7.0.31
- xorg-macros/1.20.1
- videoproto/2.3.3

## 验证结果

```bash
# xvinfo 二进制已编译
ls /storage/Users/currentUser/tmp/test-install-xvinfo-1.1.5/storage/Users/currentUser/usr/local/bin/xvinfo
# 输出: xvinfo (可执行文件)

# make check: xvinfo 无测试套件
make check
# 输出: Nothing to be done for 'check'
```

## 注意事项

1. 必须设置 PKG_CONFIG_PATH 以找到 X.Org 依赖包
2. config.status 在 HMDFS 上需要 TMPDIR 修复（E046 变体）
3. libXv 需要手动编译安装（cmd-pkgs 无预编译包）
4. xvinfo 运行需要 X 视频服务器支持（无 X server 时无法正常运行）
---

**编译结束**: 2026-06-02 11:59
**最终状态**: built
