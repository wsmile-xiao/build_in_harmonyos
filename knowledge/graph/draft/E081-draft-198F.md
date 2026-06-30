# E081: HMDFS mktemp 权限限制

**分类**: 平台限制（Platform Restriction）

**严重等级**: 🔴 高

**首次发现**: dircproxy 1.1.0 (2026-05-29)

---

## 问题描述

在 OpenHarmony/HMDFS 文件系统上，使用 autotools 构建系统时，`configure` 生成的 `config.status` 脚本会尝试使用 `mktemp -d` 创建临时目录，但 HMDFS 对这些临时目录施加了特殊的安全限制。

### 典型错误

```bash
./config.status[758]: can't create ./confXXXXXX/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

### 错误特征

- 目录创建成功，但权限为 `drwx--S---`（setgid 标志）
- 即使是目录创建者也无法写入文件
- HMDFS 的安全机制防止临时文件被篡改

---

## 根因分析

**HMDFS 文件系统的安全策略**：

1. **mktemp 安全限制**：HMDFS 可能对 `mktemp` 命令创建的目录施加额外的安全限制
2. **setgid 标志**：创建的目录带有 setgid 标志，导致权限异常
3. **防篡改机制**：这是 HMDFS 的安全设计，防止临时文件被恶意篡改
4. **副作用**：正常的编译流程无法使用这些临时目录

---

## 解决方案

### 方案 A：修改 config.status（推荐）

**适用场景**：已运行 configure，需要修改生成的 config.status

**步骤**：

1. 创建固定临时目录：
```bash
mkdir -p ./config-tmp-fixed
chmod 777 ./config-tmp-fixed
```

2. 修改 config.status 第 588-595 行：

**原代码**：
```bash
{
  tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&
  test -d "$tmp"
}  ||
{
  tmp=./conf$$-$RANDOM
  (umask 077 && mkdir "$tmp")
} || as_fn_error $? "cannot create a temporary directory in ." "$LINENO" 5
ac_tmp=$tmp
```

**修复后**：
```bash
# HMDFS workaround: use fixed directory instead of mktemp
# See E081: HMDFS mktemp permission restriction
tmp=./config-tmp-fixed
ac_tmp=$tmp
```

3. 重新运行 config.status：
```bash
./config.status
```

### 方案 B：自动化脚本（批量处理）

创建自动化脚本处理所有 autotools 软件：

```bash
#!/bin/bash
# fix-hmdfs-mktemp.sh

# 创建固定临时目录
mkdir -p ./config-tmp-fixed
chmod 777 ./config-tmp-fixed

# 修改 config.status
sed -i '588,595c\
# HMDFS workaround: use fixed directory instead of mktemp\
# See E081: HMDFS mktemp permission restriction\
tmp=./config-tmp-fixed\
ac_tmp=$tmp' config.status

echo "✅ HMDFS mktemp workaround applied"
```

---

## 受影响软件

**范围**：所有使用 autotools 构建系统的软件

**典型软件**：
- 使用 autoconf/automake 的项目
- 生成 configure 脚本的软件
- 任何调用 mktemp 创建临时目录的构建过程

**已验证案例**：
- ✅ dircproxy 1.1.0 - 修复成功

---

## 验证方法

修复后验证：

```bash
./config.status 2>&1 | grep -E "creating|error"
# 应输出：creating Makefile, creating config.h 等成功信息
# 无 Permission denied 错误

echo "✅ HMDFS workaround successful"
```

---

## 注意事项

1. **临时方案**：此修复针对生成的 config.status 文件，不修改源码
2. **每次 configure**：需要重新运行 configure 时，需重新修改 config.status
3. **自动化建议**：建议创建脚本批量处理 autotools 软件
4. **目录权限**：固定目录需要在 configure 前创建并设置适当权限
5. **非 autotools**：其他构建系统可能有类似问题，需单独处理

---

## 平台信息

**操作系统**: OpenHarmony

**文件系统**: HMDFS (Harmony Distributed File System)

**内核版本**: HongMeng Kernel 1.12.0+

**SELinux**: 启用，可能参与权限控制

---

## 相关知识条目

- E002: /tmp 只读（类似平台限制）
- E046: chmod 不生效（SELinux 限制）
- E051: 未实现的 syscall（平台能力限制）

---

## 更新历史

- **2026-05-29**: 首次发现并记录（dircproxy 编译）
- **贡献者**: 198F (协作者草稿)

---

**状态**: 草稿（Draft）- 等待主编审核合并到正式图谱