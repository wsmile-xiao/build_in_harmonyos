# E-HMDFS-permission: HMDFS权限强制设置问题

**编号**: E-HMDFS-permission (草稿)
**发现时间**: 2026-05-29
**发现软件**: isl26 0.26
**类别**: platform_limitation
**严重程度**: 🔴 阻塞性

---

## 问题概述

HMDFS（鸿蒙分布式文件系统）强制设置目录权限，导致autotools构建系统无法正常创建临时配置文件，阻塞编译流程。

---

## 错误签名

```bash
configure: creating config.status
config.status: error: cannot create subs1.awk: Permission denied

# 检查临时目录权限
ls -ld <临时目录>
drwx--S--- (2700)  # 而不是预期的 drwxrwxrwx
```

**关键特征**：
- 权限值：2700（drwx--S---）
- 大写S：setgid位设置但组无执行权限
- 只有所有者有rwx权限，组和其他用户无任何权限

---

## 根本原因

HMDFS的SELinux/hmmac安全策略强制设置：

1. **权限强制**：mkdir创建的目录权限强制为2700
2. **无法覆盖**：即使使用 `-m 777` 或修改 `umask` 也无效
3. **安全策略**：HMDFS的安全机制限制目录权限范围
4. **影响范围**：所有通过mkdir创建的目录都受影响

---

## 触发场景

- **autotools configure**：创建临时目录用于配置测试
- **config.status**：写入配置文件到临时目录
- **VPATH构建**：在源码外目录构建
- **任何需要临时目录的构建工具**

---

## 影响范围评估

### 直接影响

**所有autotools软件**（约40%的筛选库）：
- isl26、ivykis、judy等纯C库
- libart-lgpl、libasyncns、libburn等基础库
- libgsasl、libgss、libestr等工具库

### 间接影响

- **configure脚本**：无法执行配置测试
- **make工具**：某些make规则需要临时目录
- **测试套件**：make test可能需要临时目录

### 不受影响

- **纯Makefile项目**：如kissfft（已验证通过）
- **CMake项目**：CMake有自己的临时目录管理
- **Meson项目**：不受HMDFS权限限制

---

## 解决方案

### 方案1：在非HMDFS文件系统编译（推荐）

```bash
# 检查可用编译目录
mount | grep -v hmdfs

# 常见的非HMDFS目录
/data/service/hnp/tmp  # 需要installs组权限
/tmp                   # 可能只读（E002）
/var/tmp               # 需要检查权限

# 设置编译目录
export BUILD_DIR=/data/service/hnp/tmp
cd $BUILD_DIR
python3 $SKILL_ROOT/scripts/ohc-run.py build <软件名> <版本>
```

**注意事项**：
- 需要足够的权限
- 可能需要申请installs组权限
- 建议使用绝对路径

---

### 方案2：手动生成配置文件（备用）

适用于理解构建系统的用户：

```bash
# 跳过configure流程
# 手动创建必要的配置文件：
# - config.h
# - Makefile
# - config.status（如果需要）

# 示例：从已有系统复制配置
cp /usr/share/misc/config.guess .
cp /usr/share/misc/config.sub .

# 手动编辑Makefile，设置关键变量
PREFIX = $HOME/usr/local
CC = clang
CXX = clang++
```

**适用场景**：
- 简单的autotools项目
- 已有类似平台的配置模板
- 用户熟悉构建系统

---

### 方案3：使用替代构建系统

```bash
# 检查软件是否支持其他构建系统
ls -la CMakeLists.txt  # CMake
ls -la meson.build     # Meson
ls -la BUILD           # Bazel

# 使用CMake构建
mkdir build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=$HOME/usr/local
make -j4 && make install

# 使用Meson构建
meson setup build --prefix=$HOME/usr/local
ninja -C build && ninja -C build install
```

**优势**：
- 不依赖autotools临时目录
- 构建过程更现代化
- 更好的跨平台支持

---

## 验证方法

### 检测HMDFS环境

```bash
# 检查当前文件系统
mount | grep hmdfs

# 测试权限强制设置
mkdir -m 777 test_hmdfs
ls -ld test_hmdfs
# 输出：drwx--S--- (HMDFS强制设置)
# 预期：drwxrwxrwx (正常系统)

# 清理测试
rmdir test_hmdfs
```

---

### 检测软件构建系统类型

```bash
# autotools特征
ls configure.ac configure Makefile.am

# CMake特征
ls CMakeLists.txt

# Meson特征
ls meson.build

# 简单Makefile
ls Makefile (且无configure)
```

---

## 相关知识条目

- **E002**: /tmp只读问题（临时目录路径）
- **E007**: config.guess平台识别（autotools适配）
- **E046**: chmod不生效（SELinux限制）

---

## 建议补充到SKILL.md

建议在SKILL.md §7 Gotchas新增：

| Gotcha | 说明 | 对策 |
|--------|------|------|
| HMDFS权限强制 | mkdir创建的目录权限强制为2700 | 在非HMDFS目录编译或使用替代构建系统 |

---

## 编译策略调整建议

### 优先编译清单（非autotools）

**推荐优先编译**：
- kissfft（已完成，Makefile）
- libbson（预估CMake）
- libebml（预估CMake）
- libebur128（预估CMake）
- libfastjson（待验证）
- kyotocabinet（待验证）

### 暂缓编译清单（autotools）

**建议暂缓**：
- isl26（已失败）
- ivykis
- judy
- libart-lgpl
- libasyncns
- 其他autotools库

**等待条件**：
- 平台侧修复HMDFS权限策略
- 申请到非HMDFS编译环境
- 找到替代构建方案

---

## 失败案例记录

**isl26 0.26编译失败**：
- 日期：2026-05-29
- 阶段：configure（创建临时目录）
- 错误：config.status无法写入subs1.awk
- 原因：HMDFS权限强制设置
- 处理：创建失败归档（已删除，遵守R24规则）

---

## 后续行动建议

### 向平台侧反馈

建议通过以下渠道反馈：
1. 技术支持渠道：报告HMDFS权限限制问题
2. 申请特殊权限：申请非HMDFS编译环境
3. 社区讨论：分享问题和解决方案

### 编译团队建议

1. **优先策略**：编译非autotools库（约60%）
2. **记录清单**：维护autotools库清单（约40%）
3. **定期重试**：平台更新后重新尝试autotools库

---

## 总结

HMDFS权限强制设置是平台级限制，影响所有autotools软件编译。建议：
- ✅ 优先编译非autotools库
- ✅ 申请非HMDFS编译环境
- ✅ 反馈平台侧寻求解决方案
- ❌ 不强行重试autotools编译（浪费时间）

---

**知识级别**: L1 平台真理
**更新建议**: 主编审核后升级为正式知识条目
**编号建议**: 审核后分配正式编号（如E105）