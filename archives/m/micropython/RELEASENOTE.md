# MicroPython — OpenHarmony 预编译包发布说明

## 软件简介

MicroPython 是一个精简高效的 Python 3 解释器实现，专为微控制器和嵌入式系统设计。本次发布的预编译包采用 minimal 变体，无外部依赖，体积小（174KB），适合 OpenHarmony 嵌入式场景。

## 快速安装

### 方法一：直接解压（推荐）
```bash
tar xzf micropython-1.27.0-ohos-aarch64.tar.gz -C ~/usr/local
```

### 方法二：使用安装脚本
```bash
tar xzf micropython-1.27.0-ohos-aarch64.tar.gz
cd micropython-1.27.0-ohos-aarch64
sh install-micropython-1.27.0.sh
```

### 验证安装
```bash
micropython --version
# 输出: MicroPython v1.27.0 on 2026-05-14; linux [Clang 15.0.4] version

micropython -c "print('Hello from MicroPython!')"
# 输出: Hello from MicroPython!
```

## 可用版本

| 版本 | 状态 | 变体 | 补丁数 | 发布日期 | 包大小 |
|------|------|------|--------|----------|--------|
| 1.27.0 | ✅ success | minimal | 0 | 2026-05-14 | 728KB |

## 当前版本 (1.27.0) 详情

### 包内容
| 文件 | 大小 | 用途 |
|------|------|------|
| bin/micropython | 174KB | Python 解释器（minimal） |
| bin/mpy-cross | 474KB | 跨编译器（编译 .py → .mpy） |

### 编译信息
- **构建系统**: custom（Makefile）
- **构建变体**: minimal（无 libffi）
- **编译器**: clang 15.0.4
- **目标平台**: ohos-aarch64
- **质量门禁**: PASS
- **补丁数**: 0
- **测试结果**: 355 通过，566 跳过，0 失败

### minimal 变体特点
minimal 变体禁用了大部分可选功能，但核心 Python 功能完整：

✅ **支持的功能**:
- 基本语法（变量、运算、控制流）
- 数据结构（列表、字典、元组、集合）
- 函数和类定义
- 异常处理
- 模块导入系统
- 文件操作
- 字符串处理

❌ **不支持的功能**:
- FFI 调用（需要 libffi）
- 原生代码生成（viper/native）
- 异步 IO（asyncio）
- SSL/TLS
- 大部分外部模块（btree、framebuf、machine 等）

## 环境要求

### 系统要求
- **平台**: HarmonyOS/OpenHarmony
- **架构**: aarch64（64位 ARM）
- **内核**: HongMeng Kernel 1.12.0 或更高版本

### PATH 配置
确保 `~/usr/local/bin` 在 PATH 中：
```bash
echo 'export PATH="$HOME/usr/local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### 二进制签名
OpenHarmony 要求 ELF 二进制必须签名才能执行。预编译包已包含签名，可直接执行。

## 使用示例

### Python 解释器
```bash
# 启动交互式 REPL
$ micropython
>>> print("Hello")
Hello
>>> import sys
>>> sys.platform
'linux'
>>> 2**100
1267650600228229401496703205376

# 执行脚本
$ micropython script.py

# 执行单行代码
$ micropython -c "import sys; print(sys.version)"
```

### mpy-cross 跨编译器
mpy-cross 用于将 Python 代码编译为 .mpy 格式，减少内存占用和提升加载速度：
```bash
# 编译 Python 文件
$ echo "def hello(): print('Hello')" > hello.py
$ mpy-cross hello.py
$ ls hello.mpy
hello.mpy

# 在 MicroPython 中使用编译后的模块
$ micropython -c "import hello; hello.hello()"
Hello
```

## 故障排除

### 问题：permission denied
**原因**: 二进制未签名
**解决**: 使用 `ohc-run.py sign-elf` 签名二进制文件

### 问题：command not found
**原因**: PATH 未配置
**解决**: 添加 `~/usr/local/bin` 到 PATH

### 问题：模块导入失败
**原因**: minimal 变体不支持部分模块
**解决**: 查看跳过测试列表，确认模块是否支持

### 问题：需要 FFI 调用
**原因**: minimal 变体禁用 FFI
**解决**: 构建 standard 变体（需先编译 libffi）

## 更新历史

| 日期 | 版本 | 变更 |
|------|------|------|
| 2026-05-14 | 1.27.0 | 首次发布，minimal 变体 |

## 相关资源

- **软件级 README**: [README.md](README.md)
- **版本级 README**: [1.27.0/README.md](1.27.0/README.md)
- **测试报告**: [1.27.0/reports/test-report.md](1.27.0/reports/test-report.md)
- **进度记录**: [1.27.0/PROGRESS.md](1.27.0/PROGRESS.md)
- **官方网站**: https://micropython.org/
- **GitHub**: https://github.com/micropython/micropython
- **文档**: https://docs.micropython.org/

## 技术支持

如遇到问题，请查看：
1. [测试报告](1.27.0/reports/test-report.md) — 确认功能覆盖
2. [版本级 README](1.27.0/README.md) — 查看已知限制
3. [PROGRESS.md](1.27.0/PROGRESS.md) — 查看编译过程和发现的问题
