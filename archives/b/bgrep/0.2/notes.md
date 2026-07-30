# bgrep 0.2 适配笔记

## 编译环境

| 项目 | 值 |
|------|-----|
| 软件 | bgrep (binary grep) |
| 版本 | 0.2 |
| 构建系统 | makefile（极简 Makefile，仅 `all: bgrep`） |
| 语言 | C |
| 编译器 | clang 15.0.4 |
| 编译日期 | 2026-06-18 |
| 平台 | OpenHarmony aarch64 |
| 最终状态 | published |

## 软件说明

bgrep 是一个二进制模式搜索工具，类似于 grep 但用于搜索二进制/hex 字符串。支持：
- 十六进制模式搜索（如 `deadbeef`）
- 通配符搜索（`??` 代表匹配任意一字节）
- 标准输入搜索
- 目录递归搜索

源码仅包含一个 C 文件 `bgrep.c`（191 行），无外部依赖。

## 编译步骤

bgrep 源码没有 configure 脚本，只有一个极简的 Makefile（内容为 `all: bgrep`），默认使用 cc 编译。

### 1. 编译

```bash
cd $BUILD_SRC_DIR
make CC=clang CFLAGS="-fPIC -O2"
```

实际执行输出：
```
clang -fPIC -O2 -I/storage/Users/currentUser/usr/local/include -L/storage/Users/currentUser/usr/local/lib  bgrep.c   -o bgrep
```

编译一次成功，无警告无错误。

### 2. Staging 安装（R20 DESTDIR 模式）

由于 Makefile 没有 `install` 目标，手动安装：

```bash
mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/bin
cp bgrep $TEST_PREFIX/$DEFAULT_PREFIX/bin/bgrep
```

### 3. Staging 验证

```bash
$TEST_PREFIX/$DEFAULT_PREFIX/bin/bgrep 2>&1
# 输出: bgrep version: 0.2
```

### 4. 预编译包制作

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py package bgrep 0.2
```

打包流程执行了 10 步：创建打包目录 → 复制文件 → 替换符号链接 → 收集外部依赖 → 设置 RPATH → Strip → ELF 签名 → 修复执行权限 → 打包 tar.gz → 清理。

### 5. 本地安装验证

```bash
cp bgrep $DEFAULT_PREFIX/bin/bgrep
chmod 755 $DEFAULT_PREFIX/bin/bgrep
$DEFAULT_PREFIX/bin/bgrep 2>&1
# 输出: bgrep version: 0.2
```

### 6. 收尾

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py finish bgrep 0.2 published
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无 configure 脚本 | bgrep 源码仅有极简 Makefile（`all: bgrep`），非 autotools 项目 | 识别为 makefile 构建系统，直接 `make CC=clang CFLAGS="-fPIC -O2"` 编译 |
| 2 | Makefile 无 install 目标 | 原始 Makefile 极简，无 install 规则 | 手动 `cp bgrep $TEST_PREFIX/$DEFAULT_PREFIX/bin/`（R20 DESTDIR 模式） |
| 3 | G4 门禁报 "manifest 缺少 build_system" | verify_build.py 检查 manifest 中是否有 `build_system:` 字段，模板未包含 | 添加 `build_system: makefile` 到 manifest.yaml 顶层 |
| 4 | G0 clean-verify 失败 | clean-verify 脚本尝试运行不存在的 `./configure`，bgrep 无 configure 脚本 | 标记为平台限制，已手动验证通过（make 编译+功能测试均正常） |
| 5 | finish 报缺少 test-report.md | 该软件无自带测试套件，finish 前置检查需要测试报告 | 手动创建测试报告（12 项手动功能测试全部通过） |
| 6 | finish 报缺少软件级 README.md | 初始化时仅在版本目录创建了骨架 | 创建软件级 `archives/b/bgrep/README.md` |

## 源码修改

无源码修改。bgrep.c 原始代码在 OpenHarmony aarch64 上编译无需任何适配，源码 SHA256:
```
026e830563990ae08386d975348fa906a66f429c9efbdc451744ffa130d123c1
```

## 依赖版本

无外部依赖。bgrep 仅使用标准 C 库：
- `stdio.h`, `stdlib.h`, `string.h` — 标准库
- `sys/types.h`, `dirent.h` — 目录操作
- `fcntl.h`, `unistd.h`, `sys/stat.h` — 文件操作

动态链接依赖仅有 `libc.so`（musl libc）。

## 验证结果

详细测试报告见 `reports/test-report.md`，包含 12 项功能测试，全部通过。

关键验证结果：
- 二进制搜索（DEADBEEF, CAFE 等）— 偏移量正确
- 通配符搜索（`de??be`）— 功能正常
- 标准输入搜索 — 功能正常
- 目录递归搜索 — 功能正常
- 无匹配时退出码 0，无效输入退出码 2 — 符合预期
- 二进制 SHA256: 791b32b4e8202fe9182244670da623377caa1116d08f785a959419b404151843

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bgrep-0.2-ohos-aarch64.tar.gz | 82977 字节 (81KB) | 预编译包（含 ELF 签名、strip 后） |
| bgrep-0.2-ohos-aarch64-debug.tar.gz | 26647 字节 (26KB) | 调试符号包 |

## 注意事项

- bgrep 无 `--version` 选项，版本信息在无参数运行时输出到 stderr（退出码 1）
- Makefile 极简（仅 `all: bgrep`），无 install target，需手动安装
- 该软件无自带测试套件（无 make check / test target）
- 二进制类型为 PIE（Position Independent Executable），绑定模式 BIND_NOW
- 仅依赖 musl libc，无额外动态库依赖

---

**编译开始**: 2026-06-18 00:25
**编译结束**: 2026-06-18 14:28
**最终状态**: published
---

**编译结束**: 2026-07-15 17:11
**最终状态**: built
