# duperemove

## 软件描述

duperemove是一个用于查找和删除重复文件的工具，主要用于Btrfs文件系统的去重功能。它通过计算文件块的hash值来识别重复数据，并使用Btrfs的extent-same ioctl进行去重。

## 主要功能

- **文件去重**: 扫描文件系统中的重复数据块
- **Btrfs优化**: 利用Btrfs的deduplication功能减少存储空间
- **增量模式**: 支持增量扫描，避免重复计算hash
- **hash存储**: 将hash结果存储到数据库文件，支持后续快速查询

## 包含的二进制

| 程序 | 功能 |
|------|------|
| `duperemove` | 主程序，执行文件去重 |
| `hashstats` | 查看和分析duperemove生成的hash文件 |
| `btrfs-extent-same` | 测试Btrfs extent-same ioctl |

## OpenHarmony适配说明

### 平台限制

1. **statx系统调用不可用**: Linux 4.11+新增的statx syscall，OpenHarmony/musl未实现
   - 解决方案: 创建compat_statx.h兼容层，用传统stat替代

2. **libatomic库缺失**: OpenHarmony无libatomic库
   - 解决方案: 移除依赖，现代clang直接支持原子操作

3. **缺少lscpu命令**: duperemove运行时需要lscpu获取CPU信息
   - 解决方案: 可忽略，核心功能不受影响

### 依赖库

- glib-2.0 (静态链接)
- sqlite3
- blkid (来自util-linux)

### 补丁文件

| 补丁 | 说明 |
|------|------|
| 0001-Makefile.patch | 移除libatomic、静态链接glib/intl |
| 0002-compat_statx.h.patch | 新增compat_statx.h兼容层 |
| 0003-file_scan.c.patch | 引入compat_statx.h替换statx |

## 使用示例

```bash
# 扫描目录并生成hash文件
duperemove -h hashfile.db /path/to/directory

# 执行去重（需要Btrfs文件系统）
duperemove -d hashfile.db

# 查看hash文件信息
hashstats hashfile.db
```

## 功能验证结果

| 功能 | 状态 | 说明 |
|------|------|------|
| 文件扫描 | ✅ PASS | Files scanned: 4/4 (100%) |
| Hash计算 | ✅ PASS | 正常生成hash数据库 |
| hashstats | ✅ PASS | 正常读取hash文件 |
| 去重执行 | ⚠️ WARN | 需Btrfs文件系统支持 |

**质量门禁**: G1-G4 PASS

## 版本历史

| 版本 | 编译日期 | 状态 |
|------|---------|------|
| 0.15.2 | 2026-05-26 | built |

## 参考链接

- 官方网站: https://github.com/markfasheh/duperemove
- 下载地址: https://download.savannah.nongnu.org/releases/duperemove/
