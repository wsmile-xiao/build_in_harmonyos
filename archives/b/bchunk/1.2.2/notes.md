# bchunk 1.2.2 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-05-20
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 初始化编译环境：`ohc-run.py init-build bchunk 1.2.2`
2. 修改 Makefile：
   - 替换 gcc 为 clang
   - 支持 DESTDIR 和 PREFIX 环境变量
   - 使用 cp 替代 install 命令（OpenHarmony 缺少 install）
3. 编译：`make`
4. 安装（staging）：`make install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX`
5. 安装（本地）：`make install PREFIX=$DEFAULT_PREFIX`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | make install 失败：找不到 install 命令 | OpenHarmony 系统缺少 install 命令 | 修改 Makefile 使用 cp + chmod 替代 |
| 2 | 使用 gcc 编译 | Makefile 硬编码 gcc | 修改 Makefile 使用 clang |

## 源码修改

- **0001-Makefile.patch**:
  - 替换 CC=gcc 为 CC=clang
  - 替换 LD=gcc 为 LD=clang
  - 添加 DESTDIR 和 PREFIX 环境变量支持
  - 使用 mkdir + cp + chmod 替代 install 命令

## 依赖版本

无外部依赖。仅依赖标准 C 库（musl libc）。

## 验证结果

### 基本功能测试 (2026-05-21 15:25)

```bash
# T01: 版本信息
$ bchunk
binchunker for Unix, version 1.2.2 by Heikki Hannikainen <hessu@hes.iki.fi>

# T04: 文件不存在处理
$ bchunk /tmp/nonexistent.bin /tmp/nonexistent.cue output
Could not open BIN /tmp/nonexistent.bin: No such file or directory

# T05: 二进制文件检查
$ file bchunk
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)

# T08: 实际转换测试
$ bchunk -v test.bin test.cue output
Track  1: MODE1/2048   (?)  01 00:00:00
Writing tracks: output01.ugh (18KB)
```

### 测试覆盖率: 8/8 (100%)

详细测试报告: reports/test-report.md

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bchunk-1.2.2-ohos-aarch64.tar.gz | 86KB | 预编译包 |

## 注意事项

- OpenHarmony 缺少 `install` 命令，需要修改 Makefile 使用 cp 替代
- 该项目为简单 Makefile 项目，无 configure 脚本
- 无测试套件，无需运行 make check
---

**编译结束**: 2026-05-20 23:55
**最终状态**: published
