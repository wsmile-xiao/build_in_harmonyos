# E097: HMDFS umask 077 权限限制

## 基本信息

| 字段 | 值 |
|------|-----|
| 严重度 | 3 |
| 类别 | filesystem \| permission \| autotools |
| 触发工具 | configure \| config.guess \| config.status |
| 阶段 | configure |

## 错误模式

典型错误：
```bash
./config.status[725]: can't create ./confXXXXXX/subs1.awk: Permission denied
config.status: error: could not setup config files machinery

# 或
config.guess: cannot create dummy.c in temporary directory
```

错误特征：
- 临时目录创建成功但无法写入文件
- `umask 077` 创建的目录权限为 `rwx------`
- HMDFS 文件系统的特殊权限限制

## 根因分析

HMDFS（鸿蒙分布式文件系统）对 `umask 077` 创建的目录有特殊权限限制：

1. **umask 077 创建的目录**：权限变为 `rwx------`（仅用户可访问）
2. **HMDFS 安全机制**：在严格权限模式下，即使是目录所有者也可能无法写入
3. **autotools 默认行为**：`config.guess` 和 `config.status` 使用 `umask 077 && mktemp -d` 创建临时目录

这与标准 Linux 文件系统的行为不同：
- 标准 Linux：`umask 077` 创建的目录，所有者可以正常读写
- HMDFS：安全策略更严格，可能导致写入失败

## 影响范围

所有使用 autotools 构建系统的项目：
- **configure**: 使用 `umask 077 && mktemp -d` 创建临时目录
- **config.guess**: 编译测试需要创建临时文件
- **config.status**: 生成配置文件需要临时目录

典型触发场景：
- GNU autotools 项目
- OCaml configure 脚本
- 任何使用 `mktemp -d` 配合 `umask 077` 的脚本

## 推荐方案

### 方案 1: 修改脚本移除 umask 077

修改 `config.guess` 和 `config.status`：

```bash
# 原代码
tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`

# 修改为
tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`
```

同样修改 `mkdir` 命令：
```bash
# 原代码
(umask 077 && mkdir "$tmp")

# 修改为
mkdir "$tmp"
```

### 方案 2: 设置 TMPDIR 环境变量

使用不受影响的目录：
```bash
export TMPDIR=/storage/Users/currentUser/.tmp
```

### 方案 3: 使用替代临时目录创建

在 configure 前设置：
```bash
mkdir -p ~/tmp
export TMPDIR=~/tmp
```

## 禁止做法

❌ **直接修改系统 umask**
```bash
umask 022  # 影响全局，不推荐
```

❌ **跳过 configure 步骤**
原因：违反标准构建流程，可能导致后续问题

## 验证方法

```bash
# 测试 HMDFS umask 077 问题
export TMPDIR=/storage/Users/currentUser/.tmp
tmp=$((umask 077 && mktemp -d "$TMPDIR/testXXXXXX") 2>&1)
echo "tmp=$tmp"
ls -la "$tmp"
touch "$tmp/test_file"  # 如果失败则存在 HMDFS 问题
rm -rf "$tmp"
```

## 相关案例

- **OCaml 4.14.2 bootstrap**: config.guess 和 config.status 都需要修改
- **opam 2.5.0 configure**: 多个 configure 脚本需要处理

## 关联条目

- E002: /tmp 目录只读
- E099: config.guess 不识别 HarmonyOS

## 原则引用

✅ **R6**: 只改源文件不改生成文件（但 config.status 是生成文件，需特殊处理）
✅ **R23**: 平台检测机制优先于改生成文件