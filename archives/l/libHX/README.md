# libHX

## 描述
libHX 是一个 C/C++ 实用库，提供数据结构、字符串处理、文件操作等功能扩展。它设计为轻量级、跨平台，适用于系统工具开发。

## 主要功能

### 数据结构
- 链表（list）
- 树结构
- 哈希表（map）
- 双端队列（deque）

### 字符串处理
- 扩展字符串操作函数
- 字符串格式化
- 字符串解析

### 文件和目录操作
- 文件系统遍历
- 目录操作工具
- 配置文件解析

### 其他功能
- 命令行选项解析
- 进程管理
- 网络套接字辅助函数
- XML 辅助函数（可选）

## 依赖

### 核心依赖
- 无外部依赖（核心功能）

### 可选依赖
- libxml2：XML 辅助函数支持

## 编译选项

```bash
./configure --prefix=/storage/Users/currentUser/usr/local
make -j$(nproc)
make install
```

### 主要配置选项
- `--prefix`：安装路径
- `--enable-xml`：启用 XML 支持（需要 libxml2）

## 主要用途
- 系统工具开发
- 配置文件解析
- 命令行工具开发
- 跨平台应用开发

## 许可证
LGPL-2.1-or-later

## 项目地址
https://inai.de/projects/libHX/