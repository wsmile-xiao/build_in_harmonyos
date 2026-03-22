# GNU tar 1.35 for OpenHarmony

## 软件信息

| 项目 | 内容 |
|------|------|
| 软件名称 | GNU tar |
| 版本 | 1.35 |
| 官方源码 | https://ftp.gnu.org/gnu/tar/tar-1.35.tar.xz |
| 构建系统 | Autotools |

## 编译环境

| 项目 | 内容 |
|------|------|
| 操作系统 | OpenHarmony (HarmonyOS) |
| 内核 | HongMeng Kernel 1.11.0 |
| 架构 | aarch64 |
| 编译器 | clang 15.0.4 |
| 目标三元组 | aarch64-unknown-linux-ohos |

## 编译步骤

```bash
# 1. 下载并解压源码
curl -L -O https://ftp.gnu.org/gnu/tar/tar-1.35.tar.xz
tar xf tar-1.35.tar.xz
cd tar-1.35

# 2. 应用补丁
patch -p1 < 0001-port-for-ohos.patch

# 3. 创建临时目录（解决 /tmp 只读问题）
mkdir -p tmp
export TMPDIR=$PWD/tmp

# 4. 配置
./configure --prefix=$HOME/usr/local

# 5. 编译（跳过文档生成）
touch doc/tar.info
make -C gnu && make -C lib && make -C src

# 6. 安装
make install
```

## 补丁说明

### 修改文件

1. **build-aux/config.guess**: 添加 HarmonyOS 系统检测
2. **build-aux/config.sub**: 添加 ohos 操作系统支持

### 关键修改详解

#### config.guess - HarmonyOS 系统检测

**问题背景**: OpenHarmony/HarmonyOS 的 `uname -s` 返回 `HarmonyOS`，与标准 Linux 不同，需要单独处理。

**解决方案**: 在两个位置添加 HarmonyOS 支持：

1. 在 `case $UNAME_SYSTEM` 中添加 HarmonyOS 分支，设置 `LIBC=musl`
2. 在主 case 语句中添加 `aarch64:HarmonyOS:*:*` 分支，生成三元组 `aarch64-unknown-linux-ohos`

```diff
case $UNAME_SYSTEM in
+HarmonyOS)
+	# OpenHarmony/HarmonyOS uses musl libc
+	LIBC=musl
+	;;
Linux|GNU|GNU/*)

+    aarch64:HarmonyOS:*:*)
+	GUESS=$UNAME_MACHINE-unknown-linux-ohos
+	;;
    aarch64:Linux:*:*)
```

#### config.sub - ohos 操作系统支持

**问题背景**: config.sub 需要识别 `ohos` 操作系统，并允许 `linux-ohos` 内核-操作系统组合。

**解决方案**: 在三个位置添加支持：

1. 添加 `ohos*` 内核识别
2. 在 OS 验证列表中添加 `ohos*`
3. 在内核-OS 组合验证中添加 `linux-ohos*`

```diff
+	ohos*)
+		kernel=linux
+		os=ohos
+		;;

+	ohos* | gnu* | android* | bsd* | mach* | minix* | genix* | ultrix* | irix* \

+		   | linux-musl* | linux-relibc* | linux-uclibc* | linux-mlibc* \
+		   | linux-ohos* )
```

## 遇到的问题及解决方案

### 问题1: /tmp 只读

**现象**: configure 报错 `can't create temporary file /tmp/...: Read-only file system`

**原因**: OpenHarmony 系统中 /tmp 目录可能不可用

**解决方案**:
```bash
mkdir -p tmp
export TMPDIR=$PWD/tmp
```

### 问题2: makeinfo 缺失

**现象**: 编译文档时报错 `makeinfo: inaccessible or not found`

**原因**: Texinfo 工具未安装

**解决方案**: 跳过文档编译
```bash
touch doc/tar.info
```

### 问题3: libintl 链接失败

**现象**: 链接时报错 `undefined symbol: libintl_gettext`

**原因**: tar_LDADD 未包含 libintl 库

**解决方案**: 修改 src/Makefile，在 tar_LDADD 末尾添加 `$(LIBINTL)`

```makefile
tar_LDADD = ... $(LIB_SELINUX) $(LIB_SETLOCALE_NULL) $(LIBINTL)
```

## 验证结果

```bash
$ ./src/tar --version
tar (GNU tar) 1.35
Copyright (C) 2023 Free Software Foundation, Inc.
License GPLv3+: GNU GPL version 3 or later <https://gnu.org/licenses/gpl.html>.

# 功能测试
$ echo "Hello OpenHarmony!" > test.txt
$ ./src/tar czf test.tar.gz test.txt
$ ./src/tar tzf test.tar.gz
test.txt
$ ./src/tar xzf test.tar.gz -O
Hello OpenHarmony!
```

## 经验总结

1. **Autotools 适配模式**: GNU tar 使用标准 Autotools，只需修改 `config.guess` 和 `config.sub` 两个文件
2. **目标三元组**: 使用 `aarch64-unknown-linux-ohos` 格式
3. **musl libc**: HarmonyOS 使用 musl libc，在 config.guess 中设置 `LIBC=musl`
4. **libintl 依赖**: 需要确保链接时包含 libintl 库

## 参考资料

- GNU tar 官方网站: https://www.gnu.org/software/tar/
- GNU tar 源码下载: https://ftp.gnu.org/gnu/tar/
- OpenHarmony 官方网站: https://www.openharmony.cn/

---
编译日期: 2026-03-18
编译者: OpenDesk