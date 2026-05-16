# MicroPython — OpenHarmony 预编译包

## 软件简介

MicroPython 是一个精简高效的 Python 3 解释器实现，专为微控制器和嵌入式系统设计。它包含了 Python 标准库的一小部分，经过优化可在资源受限的环境中运行。

## 版本列表

| 版本 | 状态 | 构建变体 | 补丁数 | 发布日期 |
|------|------|---------|--------|----------|
| 1.27.0 | ✅ success | minimal | 0 | 2026-05-14 |

## 编译指导

### 构建系统特点
MicroPython 使用自定义 Makefile 构建系统，**无 configure 步骤**，**无 make install**。
需要手动复制文件到目标目录。

### 构建步骤
```bash
# 1. 构建 mpy-cross 跨编译器
make -C mpy-cross

# 2. 构建 Unix 端口（minimal 变体）
cd ports/unix
make VARIANT=minimal -j$(nproc)

# 3. 运行测试
make VARIANT=minimal test

# 4. 手动安装
mkdir -p ~/usr/local/bin
cp ports/unix/build-minimal/micropython ~/usr/local/bin/
cp mpy-cross/build/mpy-cross ~/usr/local/bin/
```

### 依赖要求
- **minimal 变体**: 无额外依赖（适合嵌入式场景）
- **standard 变体**: 需要 libffi 和 pkg-config（功能更完整）

## 补丁清单

### v1.27.0
- **无补丁**: 源码干净，无需修改即可在 OpenHarmony 上编译

## 已知限制

### 1. minimal 变体功能限制
minimal 变体禁用了以下功能：
- FFI 调用（缺少 libffi）
- 原生代码生成（viper、native）
- 异步 IO（asyncio）
- SSL/TLS 支持
- 大部分外部模块（btree、framebuf、machine 等）

### 2. 测试覆盖
minimal 变体测试结果：
- 通过: 355 个
- 跳过: 566 个（预期行为）
- 失败: 0 个

跳过的测试主要是需要 disabled 功能的测试，这是 minimal 变体的正常表现。

### 3. 平台限制
- OpenHarmony 要求 ELF 二进制必须签名才能执行
- 使用 `ohc-run.py sign-elf` 或 `/data/service/hnp/bin/hnpcli sign-elf`

## 功能验证

### 基本验证
```bash
$ micropython --version
MicroPython v1.27.0 on 2026-05-14; linux [Clang 15.0.4] version

$ micropython -c "print('Hello from MicroPython!')"
Hello from MicroPython!
```

### Python 语法测试
```python
# 列表操作
>>> list(5 * x + y for x in range(10) for y in [4, 2, 1])
[4, 2, 1, 9, 7, 6, 14, 12, 11, 19, 17, 16, 24, 22, 21, 29, 27, 26, 34, 32, 31, 39, 37, 36, 44, 42, 41, 49, 47, 46]

# 模块导入
>>> import sys
>>> sys.platform
'linux'

>>> import os
>>> os.listdir('.')
```

### mpy-cross 跨编译器
```bash
$ mpy-cross --version
MPY-CROSS 1.27.0

# 编译 Python 代码为 .mpy 格式
$ echo "print('Hello')" > test.py
$ mpy-cross test.py
$ ls test.mpy
test.mpy
```

## 安装使用

### 预编译包安装
```bash
# 解压并安装
tar xzf micropython-1.27.0-ohos-aarch64.tar.gz -C ~/usr/local

# 验证安装
micropython --version
mpy-cross --version
```

### 包内容
- `bin/micropython`: MicroPython 解释器（minimal 变体）
- `bin/mpy-cross`: MicroPython 跨编译器

## 相关资源

- 官方网站: https://micropython.org/
- GitHub: https://github.com/micropython/micropython
- 文档: https://docs.micropython.org/
- 源码下载: https://github.com/micropython/micropython/releases/download/v1.27.0/micropython-1.27.0.tar.xz
