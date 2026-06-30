# E108: HMDFS heredoc 限制 — 手动修改 Makefile 绕过

> **结构化数据**: [draft/E108-heredoc-makefile.kv](../draft/E108-heredoc-makefile.kv)
> **严重度**: 🟡 medium | **分类**: filesystem/hmdfs/autotools | **自动修复**: ❌ manual

---

## 错误特征

```bash
# configure 使用 heredoc 创建配置文件
cat > config.mak << EOF
PREFIX=/usr/local
CC=clang
EOF

# HMDFS 上报错或生成不完整文件
./configure: line 123: cannot create temp file for here-document: Permission denied
# 或 config.mak 只有 3 行（正常应有几十行）
```

## 根因

HMDFS 分布式文件系统不支持 shell heredoc（`cat << EOF`）语法，原因是：
1. 分布式一致性要求限制了某些 shell 操作
2. heredoc 需要临时文件缓冲，HMDFS 可能不支持
3. SELinux 策略进一步限制了文件创建权限

## 影响范围

所有使用 heredoc 创建配置文件的 autotools 项目：
- **x264** — 视频编码库（configure 创建 config.mak、config.h）
- **ffmpeg** — 多媒体框架
- **libav** — 多媒体库
- **smartmontools** — 磁盘监控工具
- 任何使用 `cat << EOF > file` 的 configure 脚本

## 解决方案

### 方案 1：手动修改 Makefile（本条目）

适用场景：Makefile 结构清晰，可手动补全缺失的定义。

**步骤**：

1. **分析 Makefile 结构**
   ```bash
   # 查看 Makefile 中的变量定义
   grep -E "^(SRCS|OBJS|CFLAGS|LDFLAGS)" Makefile
   ```

2. **添加缺失的模块定义**
   ```makefile
   # 强制编译所有 bit-depth 模块（如 x264 的 8-bit 和 10-bit）
   OBJS += $(SRCS_X:%.c=%-8.o) $(SRCS_X:%.c=%-10.o)
   
   # 强制编译 threadpool
   SRCS += common/threadpool.c
   ```

3. **手动设置编译变量**
   ```bash
   make PREFIX=$DEFAULT_PREFIX CC=clang CFLAGS="-O2 -fPIC"
   ```

4. **编译和验证**
   ```bash
   make -j$(nproc)
   ls libx264.a  # 验证静态库生成
   ```

**x264 实战案例**：

```makefile
# 在 x264 Makefile 中添加：
SRCS += common/threadpool.c

# 强制编译 8-bit 和 10-bit 模块
OBJS += $(SRCS_X:%.c=%-8.o) $(SRCS_X:%.c=%-10.o)
OBJCLI += $(SRCCLI_X:%.c=%-8.o) $(SRCCLI_X:%.c=%-10.o)

# 编译
make -j$(nproc)
# 结果：生成 1.5MB libx264.a（含所有模块）+ 222KB x264 CLI
```

## 验证

```bash
# 验证静态库大小（应大于 1MB）
ls -lh libx264.a

# 验证可执行文件
./x264 --version

# 验证包含的符号（应包含 8-bit 和 10-bit 版本）
llvm-nm libx264.a | grep x264_8_
llvm-nm libx264.a | grep x264_10_
```

## 优缺点

| 优点 | 缺点 |
|------|------|
| 不需要额外脚本 | 需要分析 Makefile 结构 |
| 产物更完整（含所有模块） | 每个项目需要定制修改 |
| 可复现性较好 | 需要手动补全变量定义 |

## 关联

- **E109** — Python 替代脚本方案（推荐，更通用）
- **E011** — HMDFS umask 077 权限问题（根因）

---
*doc/E108-heredoc-makefile.md · knowledge graph v2 · 2026-05-31 (x264 编译发现)*