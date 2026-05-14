# jo - JSON 输出工具

## 软件简介

jo 是一个命令行工具，用于从 shell 变量和参数生成 JSON 输出。它可以轻松创建 JSON 对象、数组，支持嵌套结构和类型推断。

**功能特点**:
- 从命令行参数生成 JSON 对象和数组
- 自动类型推断（字符串、数字、布尔值、null）
- 支持嵌套 JSON 结构
- 支持从文件读取数据（文本、Base64）
- 提供 Bash 和 Zsh 补全支持

**官方网站**: https://github.com/jpmens/jo

## 可用版本

| 版本 | 状态 | 编译日期 | 补丁数 | 说明 |
|------|------|----------|--------|------|
| 1.9 | partial | 2026-04-28 | 5 | 功能完整，测试全通过 |

**状态说明**:
- `success`: 完全验证通过，可直接使用
- `partial`: 功能完整，存在非阻塞问题（如 G0 自动验证失败）
- `failed`: 编译失败，不可用

## 安装方法

### 方法 1: 使用预编译包

```bash
# 下载预编译包
cd ~/usr/local
tar xzf jo-1.9-ohos-aarch64.tar.gz

# 运行安装脚本
cd jo-1.9-ohos-aarch64
sh install.sh
```

### 方法 2: 从源码编译

```bash
# 设置环境（重要！）
export TMPDIR=/storage/Users/currentUser/tmp

# 下载源码
wget https://github.com/jpmens/jo/releases/download/1.9/jo-1.9.tar.gz
tar xzf jo-1.9.tar.gz
cd jo-1.9

# 应用补丁
for patch in patches/*.patch; do
    patch -p1 < "$patch"
done

# 编译
./configure --prefix=/storage/Users/currentUser/usr/local
make -j$(nproc)

# 测试
export TMPDIR=/storage/Users/currentUser/tmp
make check

# 安装
make install
```

## 快速使用示例

```bash
# 生成 JSON 对象
jo name=John age=30
# 输出: {"name":"John","age":30}

# 生成 JSON 数组
jo -a apple banana cherry
# 输出: ["apple","banana","cherry"]

# 嵌套对象
jo person=$(jo name=John age=30)
# 输出: {"person":{"name":"John","age":30}}

# 布尔值和 null
jo enabled=true disabled=false data=null
# 输出: {"enabled":true,"disabled":false,"data":null}

# 从文件读取
echo "Hello World" > $TMPDIR/msg.txt
jo message=@$TMPDIR/msg.txt
# 输出: {"message":"Hello World"}
```

## 版本详情 (1.9)

### 编译信息

- **构建系统**: autotools
- **编译器**: clang 15.0.4
- **目标平台**: HongMeng/OpenHarmony aarch64
- **测试结果**: 27/27 通过 (100%)

### 补丁说明

本版本包含 5 个平台适配补丁：

1. `0001-tests-jo.07.sh.patch` - 测试脚本临时路径修复
2. `0002-tests-jo.15.sh.patch` - 测试脚本临时路径修复
3. `0003-tests-jo.16.sh.patch` - 测试脚本临时路径修复
4. `0004-tests-jo.24.sh.patch` - 测试脚本临时路径修复
5. `0005-tests-jo.test.patch` - 测试脚本临时路径修复

**补丁类型**: 平台适配（仅测试）
**影响范围**: 测试阶段，不影响核心功能

### 平台限制

⚠️ **重要注意事项**:

1. **临时文件路径**: HongMeng 系统的 `/tmp` 是只读文件系统（erofs），所有临时文件操作必须使用 `$TMPDIR` 环境变量。

2. **HMDFS mktemp**: configure 脚本中的 mktemp 在 HMDFS 中因权限限制可能失败，建议使用外部构建目录。

3. **环境变量**: 运行测试前必须设置 `TMPDIR=/storage/Users/currentUser/tmp`

## 功能验证

```bash
# 版本检查
jo -v
# 输出: jo 1.9

# 基本功能
jo key=value
# 输出: {"key":"value"}
```

## 参考文档

- **版本级文档**: `1.9/README.md` - 详细编译说明
- **编译进度**: `1.9/PROGRESS.md` - 编译过程记录
- **测试报告**: `1.9/reports/test-report.md` - 测试详情
- **发布说明**: `RELEASENOTE.md` - 版本发布信息

## 报告问题

如遇到问题，请检查：
1. 是否设置了 `TMPDIR` 环境变量
2. 是否应用了所有补丁
3. 编译器和依赖是否正确安装

详细问题排查请参考版本级 `PROGRESS.md` 中的"发现与知识"章节。