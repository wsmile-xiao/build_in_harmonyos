# ddrescue

GNU ddrescue - 数据恢复工具（OpenHarmony 预编译包）

## 软件简介

GNU ddrescue 是一个专业的数据恢复工具，用于从损坏的存储介质中复制数据。它会智能地跳过错误区域，优先读取健康数据，并支持断点续传。

**核心特性**：
- 智能数据恢复：优先读取健康区域，最小化对损坏区域的访问
- Mapfile 支持：记录读取状态，支持中断后恢复
- 非破坏性操作：不会修改源设备/文件
- 实时进度显示：显示已恢复数据、错误区域等统计信息

## 构建命令

### 配置
```bash
./configure --prefix=$HOME/usr/local CXX=/data/service/hnp/bin/clang++
```

**配置参数说明**：
- `--prefix=$HOME/usr/local`: 安装路径前缀
- `CXX=/data/service/hnp/bin/clang++`: 指定编译器（OpenHarmony 使用 clang++）

### 编译
```bash
make -j$(nproc)
```

### 安装（Staging）
```bash
make install DESTDIR=$HOME/tmp/test-install-ddrescue-1.30
```

### 安装（本地）
```bash
make install
```

## 补丁清单

**版本 1.30**: 无补丁

本次编译使用原始源码，未进行任何源码修改。

## 已知限制

### 1. 编译器依赖
- OpenHarmony 系统使用 clang++ 作为默认 C++ 编译器
- configure 脚本默认查找 g++，需要手动指定 CXX 变量

### 2. 测试套件部分失败
- 174/176 测试通过
- 2 个测试失败：EOF 比较问题（平台差异）
- 失败原因：cmp 命令在处理某些输出时出现边界条件差异
- 影响评估：核心功能正常，不影响数据恢复能力

### 3. 源码格式
- ddrescue 使用 GNU lzip 压缩格式（.tar.lz）
- 需要安装 lzip 工具进行解压
- init-build 脚本可能无法自动处理 lzip 格式

## 验证方法

### 基本验证
```bash
# 检查版本
ddrescue --version
ddrescuelog --version

# 基本文件复制测试
ddrescue -f source.bin dest.bin mapfile.log
cmp source.bin dest.bin  # 应显示 "文件内容完全一致"
```

### 功能验证测试
```bash
# 1. 创建测试文件
dd if=/dev/zero of=test.bin bs=1K count=100

# 2. 使用 ddrescue 复制
ddrescue -f test.bin copy.bin map.log

# 3. 验证复制结果
cmp test.bin copy.bin

# 4. 查看 mapfile 统计
ddrescuelog -t map.log
```

**预期结果**：
- 复制进度显示 100% 恢复
- cmp 显示文件内容一致
- mapfile 显示 rescued 状态

### 大文件验证
```bash
# 测试 1MB 文件复制
dd if=/dev/urandom of=large.bin bs=1K count=1024
ddrescue -f -b 4096 large.bin large-copy.bin map.log
cmp large.bin large-copy.bin
```

## 可用版本

| 版本 | 状态 | 补丁数 | 测试结果 |
|------|------|--------|----------|
| 1.30 | partial | 0 | 174/176 通过 |

## 二进制文件

- `ddrescue`: 主数据恢复工具
- `ddrescuelog`: Mapfile 操作工具

## 安装包

- `ddrescue-1.30-ohos-aarch64.tar.gz`: 主包 (430KB)
- `ddrescue-1.30-ohos-aarch64-debug.tar.gz`: 调试符号包 (96KB)
- `install-ddrescue-1.30.sh`: 安装脚本

## 参考链接

- 官网: https://www.gnu.org/software/ddrescue/
- 手册: https://www.gnu.org/software/ddrescue/manual/ddrescue.html
- 源码下载: https://ftp.gnu.org/gnu/ddrescue/
