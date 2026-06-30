# E082: LMDB robust mutex 函数缺失

## 问题概述

**错误编号**: E082  
**类别**: platform_limitation（平台限制）  
**严重程度**: medium  
**平台**: HarmonyOS  
**发现时间**: 2026-05-27  
**来源**: openldap-2.6.7 编译

## 症状描述

编译依赖 LMDB 的软件时，链接阶段出现未定义符号错误：

```bash
undefined symbol: pthread_mutexattr_setrobust
undefined symbol: pthread_mutex_consistent
```

**触发条件**：
- 使用 LMDB (Lightning Memory-Mapped Database) 的软件
- 启用 mdb 后端的 OpenLDAP
- 其他依赖 robust mutex 的数据库软件

## 根本原因

鸿蒙平台不支持 POSIX robust mutex 函数：

1. **缺失的系统调用**：
   - `pthread_mutexattr_setrobust()` - 设置 robust mutex 属性
   - `pthread_mutex_consistent()` - 恢复 robust mutex 状态

2. **LMDB 依赖机制**：
   - LMDB 使用 robust mutex 实现数据库崩溃恢复
   - 当进程崩溃时，robust mutex 允许其他进程检测并恢复锁状态
   - 鸿蒙平台缺少此机制，导致 LMDB 无法编译

3. **不是库缺失问题**：
   - pthread 库存在
   - 但 robust mutex 相关函数未实现

## 解决方案

### 禁用 mdb 后端（当前方案）

对于 OpenLDAP，禁用 mdb 后端，使用其他可用的后端：

```bash
# configure 参数
./configure --prefix=$DEFAULT_PREFIX \
    --enable-mdb=no \
    --enable-ldif=yes \
    --enable-monitor=yes \
    --enable-relay=yes
```

**可用后端**：
- **ldif**: LDIF 文件后端（文本格式）
- **monitor**: 监控后端（提供服务器状态信息）
- **relay**:  relay 后端（代理其他后端）

**不可用后端**：
- **mdb**: LMDB 后端（高性能，需要 robust mutex）
- **hdb**: BDB 后端（已废弃）
- **bdb**: BDB 后端（已废弃）

### 其他依赖 LMDB 的软件

对于其他依赖 LMDB 的软件，可能的解决方案：

1. **禁用 LMDB**：如果软件支持，禁用 LMDB 依赖
2. **使用替代方案**：使用其他数据库（如 sqlite、leveldb）
3. **等待平台更新**：如果 HarmonyOS 未来支持 robust mutex

## 功能影响

### 性能限制

禁用 mdb 后端会导致：

| 后端 | 性能 | 适用场景 |
|------|------|---------|
| mdb | ⭐⭐⭐⭐⭐ 高性能 | 生产环境首选 |
| ldif | ⭐ 低性能 | 测试/开发环境 |
| monitor | - | 监控用途 |
| relay | ⭐⭐ 中等 | 代理用途 |

**影响说明**：
- mdb 后端使用内存映射文件，读写性能极高
- ldif 后端使用文本文件，每次操作需要解析/生成 LDIF
- 生产环境不建议使用 ldif 后端

### 功能限制

1. **无法使用高性能数据库**：只能使用 ldif/monitor/relay
2. **生产环境性能受限**：不适合高负载场景
3. **迁移建议**：在其他平台编译启用 mdb 后端

## 适用范围

**受影响的软件**：
- OpenLDAP（mdb 后端）
- LMDB 库本身
- 依赖 LMDB 的软件（如 slapd）

**不受影响的软件**：
- 不使用 LMDB 的软件
- 使用其他数据库后端的软件

## 注意事项

1. **平台限制**：这是鸿蒙平台的系统调用缺失，不是软件 bug
2. **未来可能解决**：如果 HarmonyOS 支持 robust mutex，可重新编译启用 mdb
3. **迁移建议**：在其他平台编译启用 mdb 后端获得更好性能

## 验证示例

**OpenLDAP 2.6.7 编译**：

```bash
# 第一次尝试（失败）
./configure --prefix=$DEFAULT_PREFIX
make  # ❌ undefined symbol: pthread_mutexattr_setrobust

# 第二次尝试（成功）
./configure --prefix=$DEFAULT_PREFIX --enable-mdb=no --enable-ldif=yes
make  # ✅ 编译成功
make install DESTDIR=$TEST_PREFIX
```

## 参考文档

- LMDB 文档: http://www.lmdb.tech/doc/
- OpenLDAP 后端说明: https://www.openldap.org/doc/admin24/backends.html
- POSIX robust mutex: https://man7.org/linux/man-pages/man3/pthread_mutexattr_setrobust.3.html
- knowledge/graph/draft/E082-LMDB-robust-mutex.kv（结构化数据）

## 相关错误模式

- **E081**: HMDFS 临时文件限制
- **E007**: config.guess 系统识别问题

## 解决状态

✅ **已验证有效**（openldap-2.6.7 编译成功）  
⚠️ **功能限制**（无法使用 mdb 高性能后端）

---
*创建时间: 2026-05-27*  
*适用版本: LMDB/OpenLDAP mdb backend*  
*平台: HarmonyOS (OpenHarmony)*
