# E081: 鸿蒙平台缺少 Linux fallocate 常量定义

## 基本信息

| 字段 | 值 |
|------|-----|
| 严重度 | 2 |
| 类别 | platform \| constant \| header |
| 触发工具 | cc \| clang \| make |
| 阶段 | compilation |

## 错误模式

典型编译错误：
```bash
oslib/linux-blkzoned.c:389:23: error: use of undeclared identifier 'FALLOC_FL_ZERO_RANGE'
    ret = fallocate(fd, FALLOC_FL_ZERO_RANGE, z->wp, length);
                        ^
```

相关常量：
- `FALLOC_FL_ZERO_RANGE` (0x10) - 零写范围
- `FALLOC_FL_INSERT_RANGE` (0x20) - 插入范围
- `FALLOC_FL_UNSHARE_RANGE` (0x40) - 取消共享范围

## 根因分析

鸿蒙平台的内核头文件 `<fcntl.h>` 缺少部分 Linux `fallocate(2)` 的高级常量定义。

这些常量在 Linux 内核 4.x 之后引入，用于支持更精细的文件空间管理：
- `FALLOC_FL_ZERO_RANGE`: 将文件指定范围清零（不分配新块）
- `FALLOC_FL_INSERT_RANGE`: 在文件中插入空间
- `FALLOC_FL_UNSHARE_RANGE`: 取消共享块

鸿蒙平台可能：
1. 内核版本较早，未实现这些功能
2. 头文件未同步更新
3. 使用不同的 API 接口

## 影响范围

所有使用 `fallocate` 高级功能的 C/C++ 软件：
- **fio**: I/O 性能测试工具（使用 `FALLOC_FL_ZERO_RANGE` 处理 zoned block device）
- **coreutils**: 部分工具可能使用这些常量
- **文件系统工具**: 如 xfs_io、btrfs-progs 等
- **数据库系统**: PostgreSQL、MySQL 等可能使用 fallocate 管理存储空间

## 推荐方案

### 方案 1: 源码补丁（优先级高）

添加 `#ifdef __OHOS__` 守卫的常量定义：

```c
#ifdef __OHOS__
#ifndef FALLOC_FL_ZERO_RANGE
#define FALLOC_FL_ZERO_RANGE 0x10
#endif
#ifndef FALLOC_FL_INSERT_RANGE
#define FALLOC_FL_INSERT_RANGE 0x20
#endif
#ifndef FALLOC_FL_UNSHARE_RANGE
#define FALLOC_FL_UNSHARE_RANGE 0x40
#endif
#endif
```

**注意事项**：
- 必须使用 `#ifdef __OHOS__` 守卫（R8 铁律）
- 常量值必须与 Linux 内核定义一致
- 定义前需检查是否已定义（双重守卫）

### 方案 2: 配置检测（备选）

在 configure 中检测常量是否定义：
```bash
cat > conftest.c << EOF
#include <fcntl.h>
int main() { return FALLOC_FL_ZERO_RANGE; }
EOF
$CC conftest.c -o conftest 2>&1 | grep -q "undeclared"
if [ $? -eq 0 ]; then
    # 需要补充定义
fi
```

## 禁止做法

❌ **不添加 __OHOS__ 守卫直接定义常量**
```c
// 错误示例
#ifndef FALLOC_FL_ZERO_RANGE
#define FALLOC_FL_ZERO_RANGE 0x10
#endif
```
原因：污染上游代码，在其他平台可能产生冲突或掩盖真实问题

❌ **在生成文件中定义**
原因：违反 R6 铁律，生成文件修改无法保存为补丁

## 原则引用

✅ **R8**: 源码修改必须有 `#ifdef __OHOS__` 守卫
✅ **R6**: 只改源文件不改生成文件
✅ **R23**: 平台检测机制优先于改生成文件

## 验证方法

```bash
# 检查源码是否使用这些常量
grep -r "FALLOC_FL_ZERO_RANGE" src/

# 检查补丁是否包含 __OHOS__ 守卫
grep -A2 "#ifdef __OHOS__" patches/*.patch | grep "FALLOC_FL"
```

## 相关案例

- **fio 3.41**: `oslib/linux-blkzoned.c` 使用 `FALLOC_FL_ZERO_RANGE`
- **补丁**: `0001-oslib-linux-blkzoned.c.patch`

## 关联条目

- E051: 鸿蒙平台 syscall 未实现
- E020: musl FILE 结构不透明类型
- E076: fstat/lseek 返回 EACCES/EPERM