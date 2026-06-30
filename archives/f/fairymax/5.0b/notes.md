# fairymax 5.0b 适配笔记

## 编译环境
- 构建系统: makefile（plain Makefile，无 configure 脚本）
- 编译日期: 2026-06-11
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 平台: OpenHarmony (aarch64, musl libc, ld-musl-aarch64.so.1)
- 状态: published

## 编译步骤

fairymax 是一个简单的 C 语言棋类 AI 项目，使用 plain Makefile 构建，无 configure 脚本。
项目虽在 software-registry 中标注为 autotools，实际为 plain Makefile。

### 步骤 1: 初始化

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build fairymax 5.0b \
  --url=https://deb.debian.org/debian/pool/main/f/fairymax/fairymax_5.0b.orig.tar.gz
```

结果: ✅ 成功，源码解压到 ~/tmp/builds/fairymax-5.0b.work

### 步骤 2: 编译

由于无 configure 脚本，直接使用 make 编译：

```bash
cd /storage/Users/currentUser/tmp/builds/fairymax-5.0b.work
make CC=clang CFLAGS="-fPIC -O2" prefix=/storage/Users/currentUser/usr/local \
  fairymax shamax maxqi fairymax.6.gz
```

实际输出:
```
clang -fPIC -O2 -L/storage/Users/currentUser/usr/local/lib ... -DFAIRYDIR=... fairymax.c -o fairymax
fairymax.c:176:1: warning: type specifier missing, defaults to 'int' [-Wimplicit-int]
...（共 87 条警告，0 错误）
pod2man -s 6 fairymax.pod | gzip -9n > fairymax.6.gz
```

编译结果: ✅ 三个二进制 + man page 全部生成

### 步骤 2.1: Staging 安装

```bash
make install DESTDIR=/storage/Users/currentUser/tmp/test-install-fairymax-5.0b \
  prefix=/storage/Users/currentUser/usr/local
```

实际安装产物（14 个文件）:
- bin/fairymax (55680), bin/shamax (55680), bin/maxqi (39296)
- share/games/fairymax/ (fmax.ini, qmax.ini, makruk.hash)
- share/games/plugins/logos/ (3 个 png)
- share/games/plugins/xboard/ (3 个 eng)
- share/man/man6/fairymax.6.gz

### 步骤 2.2: 预编译包制作

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py package fairymax 5.0b
```

结果: ✅ fairymax-5.0b-ohos-aarch64.tar.gz (340KB)
      ✅ fairymax-5.0b-ohos-aarch64-debug.tar.gz (90KB)

### 步骤 2.3: 本地安装验证

```bash
make install prefix=/storage/Users/currentUser/usr/local
```

功能验证（XBoard 协议交互测试）:
```
$ printf "xboard\nprotover 2\nquit\n" | /storage/Users/currentUser/usr/local/bin/fairymax
tellics say     Fairy-Max 5.0b
tellics say     by H.G. Muller

$ printf "xboard\nprotover 2\nquit\n" | /storage/Users/currentUser/usr/local/bin/shamax
tellics say     ShaMax 5.0b
tellics say     by H.G. Muller

$ printf "xboard\nprotover 2\nquit\n" | /storage/Users/currentUser/usr/local/bin/maxqi
tellics say     MaxQi 4.8 (G)
tellics say     by H.G. Muller
```

三个引擎均正确响应 XBoard 协议 ✅

### 步骤 3: 收尾

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py finish fairymax 5.0b published
```

结果: ✅ finish 返回 0, manifest status=published

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无 configure 脚本，任务要求执行 `./configure --prefix=$DEFAULT_PREFIX` | 项目使用 plain Makefile，不是 autotools，software-registry 标注有误 | 直接用 `make CC=clang CFLAGS="-fPIC -O2"` 编译，跳过 configure |
| 2 | verify-build G4 FAIL（manifest 缺少 build_system 字段） | init-build 生成的 manifest 只有嵌套 `build.system` 字段，verify 脚本需要顶层 `build_system` 字段 | 手动添加顶层 `build_system: makefile` 字段并修正 `build.system` 为 makefile |
| 3 | G0 clean-verify make 命令参数解析失败 | CFLAGS="-fPIC -O2" 含空格，Python subprocess 传递给 make 时 `-O2` 被误解为 `--output-sync=2` 选项 | 属脚本平台限制，手动已验证编译可重复；configure_options 改为单字符串 `"CC=clang CFLAGS='-fPIC -O2'"` |
| 4 | 编译警告多（87 条） | 原始代码风格为 K&R C（国际象棋 AI 比赛代码），运算符优先级、隐式 int、类型转换等 | 仅警告不影响功能，遵循 R8（源码四不准则）不修改上游代码 |
| 5 | Makefile 默认 CFLAGS 含 `-s`（strip 符号） | 上游 Makefile 默认 `CFLAGS?= -O2 -s` | 编译时不使用默认 CFLAGS，改用 `CFLAGS="-fPIC -O2"`，由 packaging 管线统一 strip |

## 源码修改

无源码修改，无需补丁。

遵循 R8 铁律（源码"四不"准则）: 不修改上游代码，所有警告均为原始代码风格问题。
遵循 R6 铁律: 无源码编辑，track-edit 无变更记录。

## 依赖版本

- 无外部依赖
- 仅依赖 libc.so（musl libc，系统自带）
- 编译器: clang 15.0.4

## 预编译依赖列表

无（纯 C 单文件程序，仅依赖 libc.so）

## 验证结果

### ELF 验证

```
$ file fairymax shamax maxqi
fairymax: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)
shamax:   ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)
maxqi:    ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)
```

### 动态依赖

```
$ llvm-readelf -d fairymax | grep NEEDED
  0x0000000000000001 (NEEDED)  Shared library: [libc.so]
```

### ELF 签名

```
$ llvm-readelf -S fairymax | grep codesign
  [28] .codesign  PROGBITS  0000000000000000  012000  001000
```

三个二进制均已签名 ✅

### RPATH

```
$ llvm-readelf -d fairymax | grep RUNPATH
  0x000000000000001d (RUNPATH)  Library runpath: [$ORIGIN/../lib:$ORIGIN/../lib/external]
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| fairymax-5.0b-ohos-aarch64.tar.gz | 340KB (340553 字节) | 预编译包（3 二进制 + 数据文件 + man page + 插件配置） |
| fairymax-5.0b-ohos-aarch64-debug.tar.gz | 90KB (90145 字节) | 调试符号包（fairymax.debug, shamax.debug, maxqi.debug） |

## 知识沉淀

| 层级 | 内容 | 说明 |
|------|------|------|
| L3 | plain Makefile 项目无 configure 时的编译方法 | manifest.yaml knowledge_gained |
| L2 | makefile 类项目 CFLAGS 含空格时 G0 clean-verify 的 subprocess 限制 | 需将 configure_options 写为单字符串避免 shell 词分割 |

## 注意事项

- fairymax 是 XBoard 协议的棋类引擎，不支持常规 --help/--version CLI 参数
- 验证时通过 `printf "xboard\nquit\n" | fairymax` 测试，引擎会进入交互模式
- 项目 Makefile 默认 CFLAGS 含 `-s`（strip），编译时必须移除，由 packaging 管线统一处理
- maxqi 版本号显示为 "MaxQi 4.8 (G)" 而非 5.0b，这是上游代码行为（maxqi.c 有独立版本）---

**编译结束**: 2026-06-12 15:11
**最终状态**: published
---

**编译结束**: 2026-06-12 15:15
**最终状态**: published
