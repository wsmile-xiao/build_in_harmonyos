# entr 5.8 - OpenHarmony 发布说明

**发布日期**: 2026-05-15  
**版本**: 5.8  
**平台**: OpenHarmony aarch64 (HongMeng Kernel 1.12.0)

---

## 概述

entr (Event Notify Test Runner) 是一个命令行工具，用于监控文件变化并执行指定命令。当监控的文件发生变化时，entr 会自动触发预设的命令。

**官方项目**: https://eradman.com/entrproject/

---

## 主要功能

- **文件监控**: 监控一个或多个文件的变化
- **命令执行**: 文件变化时自动执行指定命令
- **多种模式**: 支持非交互模式、后台运行、执行后退出等
- **轻量高效**: 单一可执行文件，无外部依赖

---

## 使用示例

```bash
# 监控单个文件，变化时运行测试
echo "main.py" | entr -n python main.py

# 监控多个文件
ls *.go | entr -n go test ./...

# 监控目录（包含新增文件）
ls -d src/**/* | entr -d make

# 后台运行
echo "config.yaml" | entr -r service-restart.sh

# 执行一次后退出
echo "data.txt" | entr -z -n process-data.sh
```

---

## OpenHarmony 适配说明

### 编译参数

```bash
TARGET_OS=Linux ./configure
make PREFIX=/usr/local
make install PREFIX=/usr/local
```

### 平台特性

- 使用 inotify 实现 kqueue 接口兼容
- 支持 Linux 特有的文件系统事件

### 已知限制

- 官方测试套件依赖 tmux，未在打包版本中验证
- 手动功能测试已通过核心场景验证

---

## 测试状态

| 测试项 | 状态 | 说明 |
|--------|------|------|
| 版本验证 | ✅ | 显示正确版本号 |
| 帮助信息 | ✅ | 显示完整选项说明 |
| 文件监控 | ✅ | 检测到变化并执行命令 |
| 非交互模式 | ✅ | `-n` 选项正常工作 |
| 执行后退出 | ✅ | `-z` 选项正常工作 |
| 错误处理 | ✅ | 正确处理无效输入 |

详见 `reports/test-report.md`

---

## 安装方法

### 方法一：使用预编译包（推荐）

```bash
# 解压到临时目录
tar -xzf entr-5.8-ohos-aarch64.tar.gz -C /tmp

# 运行安装脚本
cd /tmp/entr-5.8-ohos-aarch64
./install.sh /usr/local

# 或手动安装
cp bin/entr /usr/local/bin/
cp share/man/man1/entr.1 /usr/local/share/man/man1/
```

### 方法二：从源码编译

```bash
# 下载源码
wget https://eradman.com/entrproject/code/entr-5.8.tar.gz
tar -xzf entr-5.8.tar.gz
cd entr-5.8

# 配置和编译
TARGET_OS=Linux ./configure
make PREFIX=/usr/local

# 安装
make install PREFIX=/usr/local
```

---

## 验证安装

```bash
entr -h
# 应显示帮助信息

echo "test" | entr -n echo "hello"
# 应检测到缺少文件输入的错误
```

---

## 文件清单

```
usr/local/
├── bin/
│   └── entr              # 主可执行文件
└── share/
    └── man/
        └── man1/
            └── entr.1    # 手册页
```

---

## 技术信息

- **二进制类型**: 静态链接 ELF 可执行文件
- **依赖**: 仅依赖系统 C 库（无额外依赖）
- **实现**: 通过 inotify 监控文件系统事件
- **源码修改**: 无（纯净编译）

---

## 已知问题

1. **平台检测**: 需手动设置 `TARGET_OS=Linux`
2. **测试依赖**: 完整测试套件需要 tmux

---

## 更新日志

### 5.8 (2024-XX-XX)
- 官方更新内容请查看项目官网

---

## 贡献者

- **编译**: OpenHarmony Compile Agent
- **原项目**: Eric Radman (eradman.com)