# libmikmod 3.3.13 for HarmonyOS

## 概述

libmikmod 是一款开源的模块音乐播放库，支持多种音乐模块格式（MOD、XM、S3M、IT、MED、STM、AMF、ULT、MTM、669 等）的加载与播放。本文记录其在 HarmonyOS/OpenHarmony (aarch64) 平台上的编译过程与使用方法。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | libmikmod |
| 版本 | 3.3.13 |
| 许可证 | LGPL-2.1 |
| 下载地址 | https://sourceforge.net/projects/mikmod/files/libmikmod/3.3.13/libmikmod-3.3.13.tar.gz |
| 源码校验 | SHA256: 9fc1799f7ea6a95c7c5882de98be85fc7d20ba0a4a6fcacae11c8c6b382bb207 |
| 官方网站 | https://mikmod.sourceforge.net/ |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS HongMeng Kernel 1.11.0 |
| 架构 | aarch64 |
| 编译器 | clang (LLVM) |
| 构建系统 | autotools |

## 编译依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| alsa-lib | 1.2.12 | ALSA 音频驱动支持 |
| SDL2 | 2.30.0 | SDL 音频驱动支持 |

## 编译步骤

```bash
# 设置环境变量
export PKG_CONFIG_PATH=$HOME/usr/local/lib/pkgconfig:$HOME/usr/local/share/pkgconfig
source .build-context-libmikmod-3.3.13

# 1. 初始化构建
python3 $SKILL_ROOT/scripts/ohc-run.py init-build libmikmod 3.3.13

# 2. 安装依赖（预编译包）
python3 $SKILL_ROOT/scripts/cmd-pkgs install alsa-lib/1.2.12
python3 $SKILL_ROOT/scripts/cmd-pkgs install SDL2/2.30.0

# 3. 进入源码目录
cd $BUILD_SRC_DIR

# 4. 应用平台补丁
# E007: config.guess/config.sub HarmonyOS 补丁
python3 $SKILL_ROOT/scripts/patch-autotools-ohos.pl $BUILD_SRC_DIR/autotools

# E011: configure 中 umask 077 → umask 022（HMDFS 权限修复）
sed -i 's/umask 077/umask 022/g' configure

# 5. 配置
./configure --prefix=$DEFAULT_PREFIX

# 6. 编译
make -j1

# 7. 安装到 staging 目录
make install DESTDIR=$TEST_PREFIX

# 8. 安装到实际目录
make install
```

## 补丁说明

### 0001-autotools-config.guess.patch

**目的**: 使 config.guess 脚本能识别 HarmonyOS (__OHOS__ 内核)

**修改文件**: `autotools/config.guess`

**关键修改**: 在 LIBC 检测分支和系统识别 case 分支中添加 `__OHOS__` 内核识别逻辑，
输出标准三元组 `aarch64-unknown-linux-ohos`

### 0002-autotools-config.sub.patch

**目的**: 使 config.sub 脚本能识别 `ohos-linux` 三元组

**修改文件**: `autotools/config.sub`

**关键修改**: 在操作系统列表和内核列表中添加 `ohos*` 和 `Ohos` 支持，
验证三元组 `aarch64-unknown-linux-ohos` 有效

### 0003-configure.patch

**目的**: 修复 HMDFS 文件系统上 configure 脚本的 umask 077 权限问题

**修改文件**: `configure`

**关键修改**: 将 `umask 077` 替换为 `umask 022`（2处修改：行 17787 和行 17792）

**根因**: HMDFS 的 UID 映射机制导致 umask 077 创建的临时目录（权限 0700）
对所有者映射 UID(20001006) 外的进程 UID(20020083) 不可写，
从而引发 "Permission denied" 错误。umask 022 允许组写权限，在 HMDFS 上可正常工作。

## 遇到的问题

### 问题1: config.guess 无法识别 HarmonyOS 系统 (E007)

**现象**: `./configure` 报错 "config.guess: unable to guess system type"

**原因**: libmikmod 内置的 config.guess/config.sub 脚本不包含 HarmonyOS (__OHOS__ 内核) 识别

**解决**: 使用 patch-autotools-ohos.pl 工具为 autotools 脚本打补丁

### 问题2: HMDFS umask 077 权限拒绝 (E011)

**现象**: configure 运行时报 "Permission denied" 创建临时目录失败

**原因**: HMDFS UID 映射导致 umask 077 创建的目录不可写

**解决**: 在 configure 源码中将 umask 077 改为 umask 022（遵循 R6 铁律：修补源文件，不修补生成文件）

### 问题3: 动态链接运行失败 (E050/E073)

**现象**: 运行时 `Error loading shared library libmikmod.so.3`

**原因**: HMDFS 符号链接的 UID 映射导致动态链接器无法加载 .so 文件

**解决**: 使用静态链接 `libmikmod.a` 编译程序；或直接链接 `.so.3.3.0` 文件（绕过符号链接）

## 测试结果

详见 [test-report.md](./test-report.md)

| 测试类别 | 通过 | 总数 | 结果 |
|----------|------|------|------|
| 版本号API | 4 | 4 | ✅ |
| 错误处理API | 3 | 3 | ✅ |
| 内存管理API | 9 | 9 | ✅ |
| 驱动注册与查询 | 12 | 13 | ✅ |
| 加载器注册与查询 | 9 | 13 | ✅ |
| 驱动别名查询 | 4 | 4 | ✅ |
| 类型定义完整性 | 13 | 13 | ✅ |
| 链接完整性 | 13 | 13 | ✅ |
| pkg-config | 4 | 4 | ✅ |
| 安装文件完整性 | 5 | 5 | ✅ |
| **合计** | **82** | **91** | **90.1%** |

## 验证安装

```bash
# 设置环境变量
export PKG_CONFIG_PATH=$HOME/usr/local/lib/pkgconfig:$HOME/usr/local/share/pkgconfig

# 检查版本
pkg-config libmikmod --modversion    # 应返回 3.3.13
libmikmod-config --version           # 应返回 3.3.13

# 查看链接参数
pkg-config libmikmod --libs          # -L.../lib -lmikmod
pkg-config libmikmod --cflags        # -I.../include

# 检查安装文件
ls ~/usr/local/lib/libmikmod.a       # 静态库
ls ~/usr/local/lib/libmikmod.so.3.3.0 # 动态库
ls ~/usr/local/include/mikmod.h      # 头文件

# 编写测试程序（静态链接推荐）
clang -I$HOME/usr/local/include -o myapp myapp.c \
    $HOME/usr/local/lib/libmikmod.a -lm
```

## 预编译包

| 文件 | 说明 |
|------|------|
| libmikmod-3.3.13-ohos-aarch64.tar.gz | 开发包（头文件+库文件） |
| libmikmod-3.3.13-ohos-aarch64-debug.tar.gz | 调试包 |

## 经验总结

1. **E007铁律**: 所有 autotools 项目在 HarmonyOS 上必须先用 patch-autotools-ohos.pl 补丁 config.guess/config.sub，否则 configure 无法识别系统类型
2. **E011铁律**: HMDFS 上所有 autotools 项目必须将 configure 中的 `umask 077` 改为 `umask 022`，否则 Permission denied
3. **R6铁律**: 必须修补源文件（configure），不修补生成文件（config.status）；生成文件由 configure 运行时重新生成
4. **动态库限制**: HMDFS 符号链接问题(E050)导致 .so 运行时加载失败，推荐使用静态链接

## 知识图谱引用

- E007: config.guess/config.sub HarmonyOS 补丁 (ref: E007)
- E011: HMDFS umask 077 权限修复 (ref: E011)

## 参考资料

- https://mikmod.sourceforge.net/
- https://sourceforge.net/projects/mikmod/