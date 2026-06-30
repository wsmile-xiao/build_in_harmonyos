# cdk 5.0-20260119 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-25
- 编译器: clang 15.0.4 / clang++
- 平台: aarch64-unknown-linux-ohos (HarmonyOS Kernel 1.12.0)
- 状态: built

## 编译步骤

### 1. 初始化
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build cdk 5.0-20260119 --url=https://invisible-mirror.net/archives/cdk/cdk-5.0-20260119.tgz
```

### 2. 依赖安装（ncursesw）
CDK 依赖 ncursesw（curses 开发库），任务描述标注"无依赖"不准确。

预编译包（cmd-pkgs ncurses 6.4）不含开发头文件，因此从源码编译 ncurses：
```bash
# 编译 ncurses 6.4 (--without-shared R4铁律)
python3 $SKILL_ROOT/scripts/ohc-run.py init-build ncurses 6.4 --url=https://invisible-mirror.net/archives/ncurses/ncurses-6.4.tar.gz
cd $BUILD_SRC_DIR
# 修补 config.guess/config.sub (E007)
perl $SKILL_ROOT/scripts/patch-autotools-ohos.pl config.guess config.sub
# 手动添加 linux-ohos* 到 kernel-OS validation case
./configure --prefix=$DEFAULT_PREFIX --without-shared --without-debug --without-ada --without-manpages --without-tests --without-cxx-binding --enable-widec
make -j1 && make install DESTDIR=$TEST_PREFIX && make install
```

### 3. CDK 配置
```bash
cd $BUILD_SRC_DIR
# 修补 config.guess/config.sub (E007)
perl $SKILL_ROOT/scripts/patch-autotools-ohos.pl config.guess config.sub
./configure --prefix=$DEFAULT_PREFIX --with-ncursesw --with-curses-dir=$DEFAULT_PREFIX \
  CPPFLAGS="-I$DEFAULT_PREFIX/include -I$DEFAULT_PREFIX/include/ncursesw" \
  LDFLAGS="-L$DEFAULT_PREFIX/lib" LIBS="-lncursesw"
```

### 4. 编译和安装
```bash
make -j1                    # 编译成功，1 warning (mentry.c char vs ERR comparison)
make install DESTDIR=$TEST_PREFIX  # staging 安装
make install                # 本地安装
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | E007: GNU config.guess 不含 HarmonyOS 检测分支 | 使用 patch-autotools-ohos.pl 补丁 + 手动添加 `linux-ohos*` 到 config.sub kernel-OS validation |
| 2 | CDK configure 找不到 curses 头文件 | CDK 依赖 ncursesw，任务标注无依赖不准确 | 先编译 ncurses 6.4 (--without-shared R4)，使用 `--with-ncursesw --with-curses-dir` + CPPFLAGS/LDFLAGS |
| 3 | ncurses 预编译包不含开发头文件 | cmd-pkgs ncurses 包是运行时包 | 从源码编译 ncurses 6.4 (--without-shared --enable-widec) |
| 4 | config.status mktemp 权限问题 | HMDFS: mktemp 创建的目录(umask 077)内 shell 重定向无法写入 | 修改 config.status 将 `umask 077 && mktemp` 替换为 `mkdir -p && chmod 777`（HMDFS 平台 workaround）|
| 5 | ncurses config.sub 拒绝三元组 | kernel-OS validation case 未包含 `linux-ohos*` | 在 `case $kernel-$os` 中添加 `linux-ohos*` |

## 源码修改

| 补丁文件 | 修改内容 | 类型 |
|----------|----------|------|
| 0001-config.guess.patch | 添加 __OHOS__ LIBC检测 + HarmonyOS系统识别 (13行) | 平台适配 |
| 0002-config.sub.patch | 添加 ohos-linux triplet + linux-ohos* kernel-OS validation (6行) | 平台适配 |

此外，config.status 有非源码修改（mktemp workaround），不属于补丁范围。

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| ncursesw | 6.4 | 从源码编译 (--without-shared --enable-widec) |

## 验证结果

```bash
$ cdk5-config --version
5.0.20260119

$ cdk5-config --libs
-L/storage/Users/currentUser/usr/local/lib -lcdkw -lncursesw

# 自定义测试程序编译链接成功，输出:
CDK Test: Version = 5.0.20260119
CDK Test: CDK_VERSION = 5.0

# Demo 程序: 7 个全部编译成功
# Example 程序: 38 个全部编译成功
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| cdk-5.0-20260119-ohos-aarch64.tar.gz | 13.69MB | 预编译包 (ohc-run.py package) |
| 0001-config.guess.patch | 1572B | 平台检测补丁 |
| 0002-config.sub.patch | 636B | 三元组验证补丁 |
| libcdkw.a | 440608B | CDK 静态库 (48个.o文件) |

## 注意事项

1. CDK 依赖 ncursesw，编译前需先确保 ncurses 已安装到 `$DEFAULT_PREFIX`
2. config.status 的 mktemp 权限 workaround 是 HMDFS 平台特定问题，需要在 configure 后手动修复
3. G0 干净构建验证失败（clean-verify 隔离环境缺少 ncurses 依赖），G1-G4 通过
4. CDK 是 curses 开发工具库，无命令行 --version，使用 cdk5-config 验证版本

---

**编译结束**: 2026-05-26
**最终状态**: built
---

**编译结束**: 2026-05-26 11:48
**最终状态**: published
