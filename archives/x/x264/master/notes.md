# x264 master 适配笔记

## 编译环境
- 构建系统: autotools（configure + Makefile）
- 编译日期: 2026-05-31
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

### 1. 初始化
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build x264 master --url=https://code.videolan.org/videolan/x264/-/archive/master/x264-master.tar.gz
```

### 2. 检查构建系统
x264 **不支持 CMake**，使用 autotools 构建系统。

### 3. 手动修改 Makefile（绕过 heredoc 限制）
HMDFS 不支持 heredoc，导致 configure 无法生成 config.mak 和 config.h。
解决方案：手动创建配置文件并修改 Makefile。

关键修改：
```makefile
# HMDFS 强制添加 threadpool
SRCS_X   += common/threadpool.c
SRCCLI_X += input/thread.c

# HMDFS 强制编译所有 BITDEPTH 模块（绕过 cat config.h）
OBJS      += $(SRCS_X:%.c=%-8.o) $(SRCS_8:%.c=%-8.o)
OBJS      += $(SRCS_X:%.c=%-10.o)
OBJCLI    += $(SRCCLI_X:%.c=%-8.o)
OBJCLI    += $(SRCCLI_X:%.c=%-10.o)
OBJCLI    += $(filters/video/cache-8.o filters/video/depth-8.o)
OBJCLI    += $(filters/video/cache-10.o filters/video/depth-10.o)
```

### 4. 编译
```bash
cd ~/tmp/builds/x264-master.work
make x264
```

### 5. 安装（手动）
toybox install 不支持多个源文件，需手动安装：
```bash
mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/bin $TEST_PREFIX/$DEFAULT_PREFIX/lib $TEST_PREFIX/$DEFAULT_PREFIX/include
cp libx264.a $TEST_PREFIX/$DEFAULT_PREFIX/lib/
cp x264.h x264_config.h $TEST_PREFIX/$DEFAULT_PREFIX/include/
cp x264 $TEST_PREFIX/$DEFAULT_PREFIX/bin/
```

### 6. 制作预编译包
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py package x264 master
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | x264 不支持 CMake | x264 使用 autotools 构建系统 | 使用 configure + Makefile |
| 2 | configure 无法生成配置文件 | HMDFS 不支持 heredoc (`cat << EOF`) | 手动创建 config.mak 和 config.h |
| 3 | Makefile 中缺少 10-bit CLI 对象 | 强制编译时遗漏 thread-10.o | 在 OBJCLI 中添加 SRCCLI_X:%-10.o |
| 4 | toybox install 不支持多源文件 | toybox 功能限制 | 手动复制文件 |

## 源码修改

- **Makefile**: 添加 HMDFS 强制编译规则（绕过 heredoc）
- 补丁: 0001-Makefile.patch

## 依赖版本

- 无外部依赖（x264 是独立库）

## 验证结果

```bash
$ x264 --version
x264 0.165.x
built on May 30 2026, clang: 15.0.4
x264 configuration: --chroma-format=all
libx264 configuration: --chroma-format=all
x264 license: Non-GPL commercial
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| x264-master-ohos-aarch64.tar.gz | 1905KB | 预编译包（包含 libx264.a + x264） |

## 注意事项

⚠️ **G0 干净构建验证无法通过**
- 原因：HMDFS 不支持 heredoc，导致标准 configure 流程失败
- 解决：需要手动修改 Makefile 或预置配置文件
- 建议：未来可以考虑为 x264 创建 CMakeLists.txt（社区有相关项目）

⚠️ **不支持标准安装流程**
- 原因：toybox install 功能受限
- 解决：手动复制文件或使用 Python 脚本
---

**编译结束**: 2026-05-31 15:26
**最终状态**: built
