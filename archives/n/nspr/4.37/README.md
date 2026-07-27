# NSPR 4.37 (Netscape Portable Runtime)

## 软件介绍

NSPR (Netscape Portable Runtime) 是 Mozilla 开发的跨平台可移植运行时库，为上层应用提供平台无关的 API 接口。

### 主要功能

- **线程管理**：提供跨平台的线程创建、同步和管理功能
- **IO 操作**：文件、网络、管道等 IO 操作的统一接口
- **内存管理**：内存分配、内存映射等功能
- **时间处理**：高精度计时器和时间格式化
- **进程管理**：进程创建、管道通信等
- **链接库**：动态库加载功能

### 组件说明

| 库名称 | 说明 |
|--------|------|
| libnspr4 | NSPR 核心库，提供基础平台抽象 |
| libplc4 | NSPR PLC 库，提供附加工具函数 |
| libplds4 | NSPR PLDS 库，提供数据结构 |

## NSS 依赖说明

NSPR 是 NSS (Network Security Services) 的必需依赖：

1. **编译依赖**：NSS 编译时需要 NSPR 的头文件（`nspr.h` 等）
2. **链接依赖**：NSS 编译时需要链接 NSPR 库
3. **运行依赖**：NSS 运行时需要 NSPR 动态库

### 编译 NSS 时的环境配置

```bash
# 设置 NSPR 路径
export NSPR_INCLUDE_DIR=/path/to/nspr/include/nspr
export NSPR_LIB_DIR=/path/to/nspr/lib

# 或使用 pkg-config（如果已安装）
export PKG_CONFIG_PATH=/path/to/nspr/lib/pkgconfig:$PKG_CONFIG_PATH
```

## pkg-config 使用方法

如果需要使用 pkg-config 查询 NSPR 编译参数：

### 创建 pkg-config 文件

在 `lib/pkgconfig/nspr.pc` 创建文件：

```pc
prefix=/usr/local
exec_prefix=${prefix}
libdir=${exec_prefix}/lib
includedir=${prefix}/include

Name: NSPR
Description: Netscape Portable Runtime
Version: 4.37
Libs: -L${libdir} -lnspr4 -lplc4 -lplds4
Cflags: -I${includedir}/nspr
```

### 使用 pkg-config

```bash
# 查询编译参数
pkg-config --cflags nspr    # 输出: -I/usr/local/include/nspr

# 查询链接参数
pkg-config --libs nspr      # 输出: -L/usr/local/lib -lnspr4 -lplc4 -lplds4

# 在 Makefile 中使用
CFLAGS += $(shell pkg-config --cflags nspr)
LDFLAGS += $(shell pkg-config --libs nspr)
```

## 手动使用（不使用 pkg-config）

### 编译时指定头文件

```bash
gcc -I/path/to/nspr/include/nspr -c myapp.c
```

### 链接时指定库文件

```bash
gcc -o myapp myapp.o -L/path/to/nspr/lib -lnspr4 -lplc4 -lplds4
```

### 静态链接

```bash
gcc -o myapp myapp.o /path/to/nspr/lib/libnspr4.a /path/to/nspr/lib/libplc4.a /path/to/nspr/lib/libplds4.a -lpthread -ldl
```

## 目录结构

```
archives/n/nspr/4.37/
├── bin/               # 工具程序（NSPR 无独立工具）
├── lib/               # 库文件
│   ├── libnspr4.so
│   ├── libnspr4.a
│   ├── libplc4.so
│   ├── libplc4.a
│   ├── libplds4.so
│   └── libplds4.a
├── include/           # 头文件
│   └── nspr/
│       ├── nspr.h
│       ├── prtypes.h
│       ├── prthread.h
│       └── ... (共 47 个头文件)
├── packaging/         # 预编译包
│   └── nspr-4.37-ohos-aarch64.tar.gz
├── manifest.yaml      # 元数据
└── README.md          # 本文档
```

## 注意事项

1. **编译环境**：本次编译使用 `TMPDIR=/data/storage/el2/base/cache` 作为临时目录
2. **平台**：编译目标平台为 OpenHarmony aarch64
3. **ABI 兼容**：动态库与静态库均提供，可根据需要选择链接方式
4. **线程安全**：NSPR 所有接口均为线程安全的

## 许可证

NSPR 采用 Mozilla Public License 2.0 (MPL-2.0) 许可证。

## 相关资源

- 官方文档：https://developer.mozilla.org/en-US/docs/Mozilla/Projects/NSPR
- 源代码：https://hg.mozilla.org/projects/nspr
- 发布版本：https://ftp.mozilla.org/pub/nspr/releases/