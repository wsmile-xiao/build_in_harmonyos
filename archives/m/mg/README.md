# mg — OpenHarmony 编译记录

## 基本信息

- **软件名称**: mg (micro GNU emacs)
- **描述**: 一个轻量级的 Emacs-like 文本编辑器，源自 OpenBSD
- **官方网站**: https://github.com/ibara/mg
- **编译版本**: 7.3
- **目标平台**: ohos-aarch64 (HarmonyOS ARM64)

## 版本列表

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 7.3 | published | 2026-06-08 | ✅ G0-G4 门禁全部通过 |

## 编译摘要

mg 是一个紧凑的 Emacs-like 编辑器，设计目标是保持最小化的功能集但提供完整的 Emacs 编辑体验。主要特点：

- 基于 OpenBSD mg 编辑器移植
- 内置 termcap/terminfo 支持（`--with-builtin-curses`）
- 无外部依赖（静态编译）
- 轻量级：二进制文件约 260KB

## 平台适配要点

### 1. 字节序转换函数兼容性

鸿蒙/Linux 使用标准 POSIX 字节序转换函数名，与 NetBSD/OpenBSD 不同：
- NetBSD: `le16toh/le32toh/le64toh` 等直接可用
- Linux/鸿蒙: 需通过 `<byteswap.h>` 或 `<endian.h>` 实现

**解决方案**: 创建 `compat.h` 头文件，定义兼容宏。

### 2. stat 时间戳字段名

鸿蒙/Linux 使用 `st_mtim`，而 OpenBSD 使用 `st_mtimespec`：
- OpenBSD: `sb.st_mtimespec.tv_sec/tv_nsec`
- Linux/鸿蒙: `sb.st_mtim.tv_sec/tv_nsec`

**解决方案**: 在 `fileio.c` 中替换字段名。

### 3. stdint.h 缺失

部分文件缺少 `<stdint.h>` 头文件，导致 `uint32_t` 等类型未定义。

**解决方案**: 在 `term_private.h` 中添加 `#include <stdint.h>`。

## 补丁清单

| 补丁文件 | 说明 | 类型 |
|---------|------|------|
| 0000-compat.h.patch | 创建 compat.h 兼容性头文件 | 新增文件 |
| 0002-cdbr.c.patch | 添加 compat.h 引用 | 平台适配 |
| 0003-fileio.c.patch | st_mtimespec → st_mtim 字段名修正 | 平台适配 |
| 0004-mi_vector_hash.c.patch | 添加 compat.h 引用 | 平台适配 |
| 0005-term_private.h.patch | 添加 stdint.h 引用 | 平台适配 |

## 已知限制

1. **无动态库依赖**: mg 使用内置 curses，无外部依赖
2. **无测试套**: 原始源码无 make check 目标
3. **交互式工具**: mg 是交互式编辑器，自动化测试有限

## 功能验证

```bash
# 版本检查
mg --version  # mg 7.3

# 编辑测试
echo "test" > test.txt
mg test.txt   # 成功打开编辑器

# 基本编辑命令
# C-x C-f: 打开文件
# C-x C-s: 保存文件
# C-x C-c: 退出编辑器
```

## 预编译包

- **包名**: mg-7.3-ohos-aarch64.tar.gz
- **大小**: 280KB
- **内容**: bin/mg, lib/external/
- **安装**: `curl install.sh | sh -s -- mg 7.3`

## 相关链接

- [mg GitHub 仓库](https://github.com/ibara/mg)
- [mg 官方文档](https://github.com/ibara/mg/blob/main/README)
- [mg 教程](https://github.com/ibara/mg/blob/main/tutorial)