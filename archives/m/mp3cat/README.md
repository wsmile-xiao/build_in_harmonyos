# mp3cat 0.5 for HarmonyOS

## 概述

mp3cat 在 HarmonyOS/OpenHarmony (aarch64) 上的编译指南和测试记录。

mp3cat 从字节流中提取有效的 MP3 帧，可用于：
- 清理损坏的 MP3 文件（去除非帧垃圾数据）
- 拼接 MP3 流（stdin → stdout）
- 从 mp3dir 读取 / 写入 mp3dir

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | mp3cat |
| 版本 | 0.5 |
| 上游 | https://github.com/tomclegg/mp3cat |
| 下载地址 | https://github.com/tomclegg/mp3cat/archive/refs/tags/0.5.tar.gz |
| SHA-256 | `b1ec915c09c7e1c0ff48f54844db273505bc0157163bed7b2940792dca8ff951` |
| 许可证 | GPL-2.0-or-later |
| 语言 | C |
| 构建系统 | Makefile (plain, no configure) |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS HongMeng Kernel 1.11.0 |
| 架构 | aarch64 |
| 编译器 | clang (LLVM) |
| 构建系统 | plain Makefile |

## 上游核实

### 源码与版本

- 上游仓库：`tomclegg/mp3cat`（C 实现，非 Go 版 `dmulholl/mp3cat`）
- 标签：`0.5`，对应 commit `d8582a7d53d49b47dd0387fc601772a6bf989159`
- Tarball 下载后独立计算 SHA-256：
  `b1ec915c09c7e1c0ff48f54844db273505bc0157163bed7b2940792dca8ff951`
- 文件大小：15711 字节，22 个文件（全部 `.c`/`.h` 源码 + shell 脚本 + COPYING/README/Makefile）

### 许可证

- COPYING 文件为 GPL-2.0 正文
- 源码头注释以 `$Id` 标记，无 "version 3" 字样
- 判定：**GPL-2.0-or-later**（GPLv2 正文 + "or later" 条款）

### 上游测试套件

**上游不存在正式测试套件**，完整证据链：

1. Tarball 22 个文件中无 `tests/` 或 `test/` 目录
2. 无 `test_*.c` / `*_test.c` 测试源文件
3. Makefile 仅有 `all`、`install`、`install_bin`、`install_scripts` 四个目标，**无** `check` / `test` 目标
4. 对所有 `*.c`、`*.h`、`Makefile` 执行 `grep -in "test|check|assert|unittest"` 返回零匹配
5. `example.*` 系列文件（`example.clean`、`example.logger`、`example.stream`、`example.mp3stream.sh`）为运维部署脚本（音频录制/流媒体服务器），非测试

因此需求 #3（OHOS 真跑 upstream tests）不适用；需求 #4 要求补完整证据（见 test_package/MANIFEST.yml）。

## 编译步骤

```bash
# 1. 下载源码
curl -fsSL -o mp3cat-0.5.tar.gz \
  https://github.com/tomclegg/mp3cat/archive/refs/tags/0.5.tar.gz

# 2. 解压
tar xzf mp3cat-0.5.tar.gz
cd mp3cat-0.5

# 3. 应用补丁
patch -p1 < patches/0001-Makefile.patch
patch -p1 < patches/0002-mp3cat.c.patch

# 4. 编译（静态链接）
make CC=clang CFLAGS="-O2" LDFLAGS="-static" -j1
```

## 补丁说明

### 0001-Makefile.patch

**目的**: 将硬编码的 `cc` 替换为 `$(CC)`/`$(CFLAGS)`/`$(LDFLAGS)`，并添加 `DESTDIR` 支持

**修改文件**: `Makefile`

**关键修改**:
- `CC?=cc` — 允许 Conan 注入编译器
- `CFLAGS?=` / `LDFLAGS?=` — 允许传入编译/链接选项
- `$(CC) $(CFLAGS) -o mp3cat *.c $(LDFLAGS)` — 替换 `cc -o mp3cat *.c`
- `$(DESTDIR)$(PREFIX)/bin` — 安装路径支持 staging

### 0002-mp3cat.c.patch

**目的**: 添加 `--version` 和 `--help` 标志，用于 CLI 冒烟测试

**修改文件**: `mp3cat.c`

**关键修改**: 在 `--tail` 参数处理块之后插入 `--version`（打印版本并 exit 0）和 `--help`（打印用法并 exit 0）分支。

## test_package

上游无测试套件，test_package 填补该空缺，验证真实 CLI 行为：

- **MP3 fixture**: 程序化构造的最小有效 MP3 帧（MPEG-1 Layer I, 64kbps, 32kHz, 96 字节/帧），非提交来历不明的二进制
- **Fixture SHA 校验**: 使用前验证 fixture SHA-256
- **行为断言**:
  - `--version` → exit 0
  - `--help` → exit 0
  - 3 帧透传 → 192 字节（lookahead 丢弃末帧）
  - 垃圾+3 帧清洗 → 192 字节（垃圾被剥离），输出与透传一致
  - 空输入 → exit 0, 0 字节
  - 错误用法（1 个位置参数）→ exit 1

## 验证安装

```bash
# 检查二进制
ls -la $HOME/usr/local/bin/mp3cat

# 检查版本
mp3cat --version

# 检查拼接行为
mp3cat - - < input.mp3 > output.mp3
```

## 参考资料

- https://github.com/tomclegg/mp3cat
- http://tomclegg.net/mp3cat
