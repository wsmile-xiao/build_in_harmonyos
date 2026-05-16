# MicroPython 1.27.0 — OpenHarmony 编译记录

## 基本信息

| 项目 | 详情 |
|------|------|
| 软件 | micropython |
| 版本 | 1.27.0 |
| 构建系统 | custom（Makefile） |
| 构建变体 | minimal |
| 目标平台 | ohos-aarch64 |
| 编译器 | clang 15.0.4 |
| 状态 | ✅ success |

## 编译指导

### 构建系统特点
MicroPython 使用自定义 Makefile 构建系统：
- ❌ **无 configure 步骤**
- ❌ **无 make install**
- ✅ 需手动复制文件到目标目录
- ✅ 支持多种变体（minimal/standard）

### 构建命令
```bash
# Step 1: 构建 mpy-cross 跨编译器
cd ~/builds/micropython-1.27.0.work
make -C mpy-cross -j$(nproc)

# Step 2: 构建 Unix 端口（minimal 变体）
cd ports/unix
make VARIANT=minimal -j$(nproc)

# Step 3: 运行测试
make VARIANT=minimal test

# Step 4: 手动安装到 DESTDIR
source .build-context-micropython-1.27.0
mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/bin
cp ports/unix/build-minimal/micropython $TEST_PREFIX/$DEFAULT_PREFIX/bin/
cp mpy-cross/build/mpy-cross $TEST_PREFIX/$DEFAULT_PREFIX/bin/

# Step 5: 二进制签名（OpenHarmony 要求）
ohc-run.py sign-elf $TEST_PREFIX/$DEFAULT_PREFIX/bin/micropython
ohc-run.py sign-elf $TEST_PREFIX/$DEFAULT_PREFIX/bin/mpy-cross

# Step 6: 打包预编译包
ohc-run.py package micropython 1.27.0
```

### 为什么选择 minimal 变体？
OpenHarmony 平台缺少 libffi 库，minimal 变体不需要外部依赖，可独立运行。虽然功能受限，但核心 Python 解释器功能完整。

### minimal vs standard 对比
| 特性 | minimal | standard |
|------|---------|----------|
| libffi 依赖 | ❌ 不需要 | ✅ 需要 |
| 原生代码生成 | ❌ 禁用 | ✅ 支持 |
| asyncio | ❌ 禁用 | ✅ 支持 |
| SSL/TLS | ❌ 禁用 | ✅ 支持 |
| 二进制大小 | 174KB | ~500KB+ |
| 测试通过率 | 355/921 | 更多 |

## 补丁清单

### 本版本补丁
- **补丁数量**: 0
- **原因**: 源码干净，无需修改即可在 OpenHarmony 上编译

## 已知限制

### 1. 网络问题
GitHub tarball 下载失败（HTTPS 连接超时），需从镜像源克隆：
```bash
git clone --depth 1 --branch v1.27.0 https://gitee.com/mirrors/micropython.git
```

### 2. minimal 变体功能限制
禁用功能列表：
- FFI 调用（无 libffi）
- 原生代码生成（viper、native）
- 异步 IO（asyncio）
- SSL/TLS 支持
- 外部模块（btree、framebuf、machine、websocket 等）

### 3. 自定义构建系统适配
- 无 configure → clean-verify 无法运行 G0 验证
- 无 make install → 需手动复制文件

### 4. 二进制签名
OpenHarmony 要求 ELF 二进制必须签名才能执行：
```bash
ohc-run.py sign-elf micropython
```

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
>>> import sys
>>> sys.platform
'linux'

>>> import os
>>> os.listdir('.')[:5]

# 数学运算
>>> 2**100
1267650600228229401496703205376

# 字符串操作
>>> "hello" * 3
'hellohellohello'
```

### mpy-cross 跨编译器验证
```bash
$ mpy-cross --version
MPY-CROSS

# 编译测试
$ echo "print('test')" > test.py
$ mpy-cross test.py
$ ls test.mpy
```

## 构建产物

### 二进制文件
| 文件 | 大小 | 用途 |
|------|------|------|
| micropython | 174KB | Python 解释器（minimal） |
| mpy-cross | 474KB | 跨编译器（编译 .py → .mpy） |

### 预编译包
| 文件 | 大小 | 内容 |
|------|------|------|
| micropython-1.27.0-ohos-aarch64.tar.gz | 728KB | 可执行文件 |
| micropython-1.27.0-ohos-aarch64-debug.tar.gz | 39KB | 调试符号 |

## 编译历史

| 日期 | 事件 |
|------|------|
| 2026-05-14 | 初始化构建环境 |
| 2026-05-14 | 构建 mpy-cross 成功 |
| 2026-05-14 | 构建 minimal 变体成功 |
| 2026-05-14 | 运行测试：355 通过，566 跳过 |
| 2026-05-14 | 打包预编译包成功 |
| 2026-05-14 | 安装验证成功 |

## 相关链接

- [软件级 README](../README.md) — 安装指南和功能说明
- [PROGRESS.md](PROGRESS.md) — 详细编译过程记录
- [测试报告](reports/test-report.md) — 测试执行详情
- [质量报告](reports/quality-report.md) — 质量门禁结果
