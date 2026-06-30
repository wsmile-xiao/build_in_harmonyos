# libpst - Microsoft Outlook PST 文件读取库

## 简介

libpst 是一个用于读取 Microsoft Outlook PST 文件（Personal Storage Table，个人存储表）的开源库。PST 文件是 Outlook 用于存储电子邮件、联系人、日历等数据的专有格式。

## 主要功能

- 解析 PST 文件结构
- 提取邮件、联系人、日历等数据
- 提供命令行工具进行 PST 文件操作

## OHOS 适配说明

### 关键问题

**HMDFS SELinux 权限限制**：libpst 默认使用 autotools 构建系统，但在 HMDFS 文件系统上，hmmac 强制访问控制会阻止 autotools 创建/写入临时文件，导致 configure 失败。

### 解决方案

1. **构建系统切换**：使用 cmake 替代 autotools
2. **自定义 CMakeLists.txt**：创建完整的 cmake 构建配置（350+ 行）
3. **getopt 冲突修复**：修改 XGetopt.h，添加条件判断避免与系统 getopt 冲突

### 编译命令

```bash
# 使用 cmake 构建
cmake .. \
  -DCMAKE_BUILD_TYPE=Release \
  -DZLIB_LIBRARY=/path/to/libz.a \
  -DZLIB_INCLUDE_DIR=/path/to/include \
  -DENABLE_STATIC_TOOLS=ON \
  -DENABLE_SHARED=OFF \
  -DENABLE_PYTHON=OFF \
  -DENABLE_DII=OFF \
  -DENABLE_MSG_UTILS=OFF
make
make install DESTDIR=/path/to/staging
```

### 功能限制

当前构建**缺少以下工具**（需要 libgsf-1 依赖）：
- `readpst`：主要的 PST 文件转换工具
- `pst2ldif`：PST 转 LDIF 格式工具
- `nick2ldif`：Nickname 转 LDIF 工具

**可用工具**：
- `lspst`：PST 文件列表工具
- `getidblock`：获取 PST 数据块工具
- `dumpblocks`：dump 数据块工具

### 依赖

- **zlib**：压缩库（已安装）
- **libgsf-1**：GNOME 结构化文件库（可选，用于 msg-based 工具）
- **glib**：GLib 库（可选，libgsf 的依赖）
- **libxml2**：XML 库（可选，libgsf 的依赖）

## 已编译版本

- **0.6.76** (2026-05-25) - 首次编译，使用 cmake 成功绕过 HMDFS SELinux 限制

## 补丁说明

- `0001-CMakeLists.txt.patch`：新增 cmake 构建配置文件
- `0002-src-XGetopt.h.patch`：修复 getopt 冲突问题

## 参考资料

- 官方网站：http://www.five-ten-sg.com/libpst/
- 源码下载：http://www.five-ten-sg.com/libpst/packages/