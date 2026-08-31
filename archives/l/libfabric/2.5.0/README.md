# libfabric 2.5.0 — OpenHarmony (OHOS) 交叉编译归档

## 基本信息

| 项目 | 值 |
|------|-----|
| 软件名称 | libfabric (OpenFab Interfaces) |
| 版本 | 2.5.0 |
| 目标平台 | aarch64-unknown-linux-ohos (HarmonyOS, 鸿蒙内核 1.12.0) |
| 构建系统 | autotools (configure + make) |
| 编译器 | clang-15 (OHOS 交叉编译工具链) |
| 编译状态 | built |
| 编译日期 | 2026-05-27 |

## 源码信息

- **下载地址**: https://github.com/ofiwg/libfabric/releases/download/v2.5.0/libfabric-2.5.0.tar.bz2
- **SHA256**: `276019edca708dc0569cf3064a412e395ba7b1883299781caed120594f850995`
- **压缩格式**: tar.bz2

## 简介

libfabric(OpenFab Interfaces, OFI)是一个高性能通信框架库，为应用程序提供标准的API接口，支持多种网络通信provider(sockets、TCP、UDP、RXM、SHM、MRail等)。它是OFI工作组(OFI-WG)开发的开源项目，广泛应用于高性能计算(HPC)和数据中心场景。

本归档为libfabric 2.5.0在OpenHarmony(OHOS) aarch64平台的交叉编译版本。

## 编译配置

```bash
./configure --prefix=/storage/Users/currentUser/usr/local --enable-monitor=no
make -j1
make install
```

- `--enable-monitor=no`: 禁用monitor provider(OHOS无fstab.h头文件)

## 补丁列表

本归档包含4个补丁,用于适配OHOS平台和HMDFS文件系统:

| 序号 | 补丁文件 | 类型 | 守卫宏 | 说明 |
|------|---------|------|--------|------|
| 1 | 0001-config-config.guess.patch | platform | `__OHOS__` | OHOS平台检测,输出`aarch64-unknown-linux-ohos` |
| 2 | 0002-config-config.sub.patch | platform | `__OHOS__` | OHOS目标三元组支持(linux-ohos模式) |
| 3 | 0003-configure.patch | filesystem | N/A | mktemp使用`$TMPDIR`绝对路径(HMDFS兼容) |
| 4 | 0004-src-unix-osd.c.patch | platform | `__OHOS__` | 排除`cpu_set_t`和`pthread_setaffinity_np`(OHOS guard) |

## 交付物

### 预编译包

| 文件 | 大小 | 说明 |
|------|------|------|
| packaging/libfabric-2.5.0-ohos-aarch64.tar.gz | 6.3 MB | 主预编译包(bin+lib+include+share) |
| packaging/libfabric-2.5.0-ohos-aarch64-debug.tar.gz | 863 KB | Debug符号包 |

### 预编译包内容

主包包含203个文件/目录:

- `bin/fi_info` — 信息查询工具(31 KB)
- `bin/fi_strerror` — 错误码查询工具(23 KB)
- `bin/fi_pingpong` — 延迟/带宽测试工具(56 KB)
- `lib/libfabric.so.1.31.0` — 共享库(1.0 MB, 主要交付物)
- `lib/libfabric.so` → `libfabric.so.1` → `libfabric.so.1.31.0` — 符号链接
- `lib/libfabric.a` — 静态库(2.0 MB)
- `lib/pkgconfig/libfabric.pc` — pkg-config文件
- `include/rdma/*.h` — 14个核心API头文件
- `include/rdma/providers/*.h` — 3个provider头文件
- `share/man/` — 大量man页面(man1, man3, man7)

### 二进制特征

- **架构**: ELF 64-bit LSB arm64
- **动态链接器**: `/lib/ld-musl-aarch64.so.1` (OHOS musl libc)
- **SONAME**: `libfabric.so.1`
- **符号版本**: FABRIC_1.0 ~ FABRIC_1.9 (11个ABI版本)
- **导出函数**: 36个核心API函数
- **依赖**: 仅 libc.so (OHOS musl libc)

## 关键适配问题

### 问题1: fstab.h 缺失
- **根因**: OHOS不提供fstab.h头文件,prov/hook/monitor依赖此文件
- **解决**: 禁用monitor provider(`--enable-monitor=no`)
- **影响**: 文件系统监控功能不可用,对核心通信功能影响极小

### 问题2: pthread_setaffinity_np 和 cpu_set_t 缺失
- **根因**: OHOS(musl libc)不提供`pthread_setaffinity_np`函数和`cpu_set_t`类型
- **解决**: 在`src/unix/osd.c`中添加`__OHOS__`条件编译守卫
  - `#elif defined __linux__ && !defined(__OHOS__)` 排除OHOS的`cpu_set_t` typedef
  - `#if !defined(__APPLE__) && !defined(__OHOS__)` 排除OHOS的`pthread_setaffinity_np`调用
- **影响**: `ofi_set_thread_affinity`返回`-FI_ENOSYS`,线程CPU亲和性不可用,不影响核心通信

### 问题3: HMDFS mktemp 相对路径失败
- **根因**: HMDFS文件系统不支持`mktemp -d "./confXXXXXX"`相对路径创建临时目录
- **解决**: 修改configure中mktemp为`${TMPDIR:-/storage/Users/currentUser/tmp}/confXXXXXX`绝对路径
- **影响**: configure/config.status在HMDFS上可正常运行

### 问题4: HMDFS硬链接不支持
- **根因**: HMDFS不支持硬链接(ln操作返回`Operation not permitted`)
- **解决**: libtool自动回退为复制,非致命
- **影响**: 构建警告,不影响最终产物

## 注意事项

1. **RUNPATH问题**: 三个可执行文件(fi_info, fi_strerror, fi_pingpong)包含autotools生成的RUNPATH(`/storage/Users/currentUser/usr/local/lib`)。共享库本身不含RUNPATH。生产环境部署前应使用`patchelf --remove-rpath`清除可执行文件的RUNPATH。

2. **TMPDIR配置**: configure补丁硬编码了`/storage/Users/currentUser/tmp`作为TMPDIR回退值,因为HMDFS上/tmp不可写。根据目标部署环境可能需要调整此路径。

3. **make check通过**: 本机为 aarch64 Linux（musl libc），可直接运行交叉编译产物（ELF arm64, dynamic /lib/ld-musl-aarch64.so.1）。`make check` 1/1 PASS，fi_info 正常输出 16 个 provider 信息。fabtests 是独立仓库不在 tarball 中，不纳入。

4. **monitor provider不可用**: 已禁用,OHOS平台文件系统监控功能不可用。

5. **线程亲和性不可用**: `ofi_set_thread_affinity`在OHOS上返回`-FI_ENOSYS`。

## 使用方法

### 安装预编译包

```bash
# 解压主包到目标安装目录
tar xzf libfabric-2.5.0-ohos-aarch64.tar.gz -C /path/to/install/

# 设置环境变量
export LD_LIBRARY_PATH=/path/to/install/lib
export PATH=/path/to/install/bin:$PATH
```

### 编译依赖项目

```bash
# 使用pkg-config
export PKG_CONFIG_PATH=/path/to/install/lib/pkgconfig
gcc -o myapp myapp.c $(pkg-config --cflags --libs libfabric)
```

## 依赖关系

- **编译依赖**: 无(OHOS工具链自带必需组件)
- **运行依赖**: libc.so (OHOS musl libc)

## 归档文件结构

```
archives/l/libfabric/2.5.0/
├── README.md              # 本文件
├── manifest.yaml          # 版本manifest(ARCHIVE-SPEC v2.0)
├── notes.md               # 编译适配笔记
├── packaging/             # 预编译包
│   ├── libfabric-2.5.0-ohos-aarch64.tar.gz      # 主包(6.3 MB)
│   └── libfabric-2.5.0-ohos-aarch64-debug.tar.gz # Debug包(863 KB)
├── patches/               # 补丁文件(4个)
│   ├── 0001-config-config.guess.patch
│   ├── 0002-config-config.sub.patch
│   ├── 0003-configure.patch
│   └── 0004-src-unix-osd.c.patch
└── reports/                # 测试报告
    ├── quality-report.md  # 质量门禁报告
    └── test-report.md      # 详细测试报告
```