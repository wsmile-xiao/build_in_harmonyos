# libcap-ng 0.9.1 鸿蒙版

## 软件描述
libcap-ng 是一个简化 POSIX capabilities（能力）编程的 Linux 库。该库提供实用工具来帮助分析系统中可能具有过多权限的应用程序。

## 功能特性
- 简化的 POSIX 能力编程接口
- C 语言绑定（本构建禁用了 Python3 绑定）
- 实用工具：pscap、filecap、netcap、captest
- libdrop_ambient.so 用于环境能力管理

## 编译方法

由于 autotools 配置脚本在鸿蒙系统上的兼容性问题，本版本使用手动 Makefile 方式编译。

### 构建步骤：
```bash
# 1. 下载源码
curl -L -k -o v0.9.1.tar.gz https://github.com/stevegrubb/libcap-ng/archive/refs/tags/v0.9.1.tar.gz
tar -xzf v0.9.1.tar.gz

# 2. 手动创建 config.h
# （为鸿蒙系统创建特定的配置定义）

# 3. 使用手动 Makefile 构建
make -f Makefile.manual

# 4. 运行测试
./lib_test
./thread_test

# 5. 安装
make -f Makefile.manual install PREFIX=/your/install/path
```

## 依赖说明

### 必需依赖：
- gcc 编译器
- Linux 内核头文件 (linux/capability.h)
- pthread 线程库

### 可选依赖：
- Python3（用于 Python 绑定，本构建未启用）
- libbpf、libaudit、clang、bpftool（用于 cap-audit，未构建）

## 已知问题

1. **Autotools 兼容性**：标准的 autotools 配置脚本在鸿蒙系统上无法工作，原因如下：
   - config.guess 无法识别鸿蒙系统类型
   - Git 仓库的 configure 脚本不完整
   
2. **解决方案**：创建手动 Makefile 绕过 autotools 问题

3. **平台支持**：libcap-ng 需要 Linux 特有的头文件和能力系统调用，专为 Linux 系统设计，可能需要在鸿蒙内核上进行适配

## 安装组件

### 库文件：
- libcap-ng.so.0.0.1 - 主共享库
- libcap-ng.a - 静态库
- libdrop_ambient.so.0.0.0 - 环境能力释放库

### 头文件：
- cap-ng.h - 库头文件

### 实用工具：
- pscap - 显示进程能力
- filecap - 显示文件能力
- netcap - 显示网络进程能力
- captest - 测试能力功能

## 许可证
GNU LGPL v2.1（库）
GNU GPL v2（实用工具）

## 原始源码
https://github.com/stevegrubb/libcap-ng

