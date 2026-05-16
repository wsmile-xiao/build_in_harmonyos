# Knowledge Report — libdvdcss 1.5.0

## 编译知识整理

本文档记录在编译 libdvdcss 1.5.0 过程中获得的知识和经验。

---

## 1. 软件基本信息

### 1.1 软件概述
- **名称**: libdvdcss
- **版本**: 1.5.0
- **许可证**: GNU General Public License (GPL)
- **官方网站**: https://www.videolan.org/developers/libdvdcss.html
- **用途**: DVD CSS解密库，用于合法的DVD媒体播放

### 1.2 核心功能
- 提供DVD内容解密功能
- 支持CSS（Content Scramble System）解密
- 跨平台支持（Linux, Windows, macOS等）
- 简洁的API设计

### 1.3 构建系统
- **主要构建系统**: Meson (推荐)
- **备选构建系统**: Autotools (configure/make)
- **构建工具**: Ninja
- **语言**: C

---

## 2. 编译环境配置

### 2.1 编译器要求
- **推荐编译器**: Clang 15.0.4 或 GCC
- **C标准**: C17 (可配置)
- **目标平台**: OpenHarmony aarch64

### 2.2 构建工具依赖
| 工具 | 版本要求 | 说明 |
|------|----------|------|
| meson | >= 0.60.0 | 主要构建系统 |
| ninja | >= 1.8.0 | 构建后端 |
| clang/gcc | >= 10.0 | C编译器 |
| pkg-config | >= 0.29 | 包配置工具 |

### 2.3 运行依赖
**无外部依赖**

libdvdcss 是一个独立的库，不需要其他第三方库。

---

## 3. 构建流程详解

### 3.1 Meson构建（推荐）

#### 步骤1: 配置
```bash
meson setup build --prefix=/usr/local
```

**关键配置选项**:
- `buildtype=debugoptimized` - 调试优化构建
- `c_std=c17` - 使用C17标准
- `default_library=both` - 同时构建静态库和动态库
- `warning_level=2` - 中等警告级别

#### 步骤2: 编译
```bash
meson compile -C build
```

**编译产物**:
- 动态库: libdvdcss.so.2.3.0 (约83KB)
- 静态库: libdvdcss.a (约206KB)
- 头文件: 3个 (dvdcss.h, dvdcpxm.h, version.h)

#### 步骤3: 安装
```bash
meson install -C build
```

### 3.2 关键编译特性

#### 特性检测
Meson会自动检测以下特性：
- `HAVE_LINUX_DVD_STRUCT` - Linux DVD结构支持
- `DVD_STRUCT_IN_LINUX_CDROM_H` - DVD ioctl支持
- `SUPPORT_ATTRIBUTE_VISIBILITY_DEFAULT` - 函数可见性属性

#### 配置文件生成
- `config.h` - 根据平台特性自动生成
- 包含所有编译时检测的宏定义

---

## 4. API使用指南

### 4.1 头文件结构
```
include/dvdcss/
├── dvdcss.h      # 主API头文件
├── dvdcpxm.h     # CPXM扩展API
└── version.h     # 版本信息
```

### 4.2 核心API函数

| 函数 | 说明 | 示例 |
|------|------|------|
| dvdcss_open | 打开DVD设备 | `dvdcss_t h = dvdcss_open("/dev/dvd");` |
| dvdcss_close | 关闭设备 | `dvdcss_close(h);` |
| dvdcss_read | 读取数据 | `dvdcss_read(h, buffer, blocks, flags);` |
| dvdcss_seek | 定位位置 | `dvdcss_seek(h, offset, flags);` |
| dvdcss_error | 获取错误 | `const char *err = dvdcss_error(h);` |
| dvdcss_is_scrambled | 检查加密 | `int enc = dvdcss_is_scrambled(h);` |

### 4.3 重要常量

```c
#define DVDCSS_BLOCK_SIZE      2048    // DVD块大小
#define DVDCSS_NOFLAGS         0       // 无标志
#define DVDCSS_READ_DECRYPT    (1<<0)  // 解密读取
#define DVDCSS_SEEK_MPEG       (1<<0)  // MPEG定位
#define DVDCSS_SEEK_KEY        (1<<1)  // 密钥检查
```

### 4.4 使用示例

#### 基本使用流程
```c
#include <dvdcss/dvdcss.h>

int main() {
    // 1. 打开设备
    dvdcss_t dvd = dvdcss_open("/dev/dvd");
    if (!dvd) {
        fprintf(stderr, "Error: %s\n", dvdcss_error(NULL));
        return -1;
    }
    
    // 2. 定位到特定块
    dvdcss_seek(dvd, 0, DVDCSS_NOFLAGS);
    
    // 3. 读取数据（自动解密）
    char buffer[DVDCSS_BLOCK_SIZE];
    dvdcss_read(dvd, buffer, 1, DVDCSS_READ_DECRYPT);
    
    // 4. 关闭设备
    dvdcss_close(dvd);
    
    return 0;
}
```

#### 链接方式
```bash
# 动态链接
gcc myapp.c -ldvdcss

# 静态链接
gcc myapp.c /path/to/libdvdcss.a

# 使用pkg-config
gcc myapp.c $(pkg-config --cflags --libs libdvdcss)
```

---

## 5. 平台适配知识

### 5.1 Linux/OpenHarmony适配
- 支持 Linux DVD ioctl
- 使用 `<linux/cdrom.h>` 结构
- POSIX兼容API

### 5.2 编译选项优化
- `-D_DEFAULT_SOURCE` - 启用默认特性
- 使用 `-fvisibility=default` 导出符号
- 静态库使用 `llvm-ar` 打包

### 5.3 跨平台注意事项
- Windows需要不同的ioctl实现
- macOS需要 IOKit framework
- 不同平台的DVD设备路径不同

---

## 6. 测试验证知识

### 6.1 功能测试要点
- 验证所有API函数可调用
- 测试NULL参数安全处理
- 验证错误返回值
- 测试符号解析完整性

### 6.2 质量检查标准
- **G1**: 二进制完整性 - 无缺失符号
- **G2**: 功能可用性 - API可调用
- **G3**: 可移植性 - 符合标准
- **G4**: 档案完整性 - 文件完整

### 6.3 测试程序设计
```c
// 基本测试框架
int test_passed = 0, test_failed = 0;

// 测试 dvdcss_open(NULL)
dvdcss_t h = dvdcss_open(NULL);
if (h == NULL) {
    test_passed++;
    printf("PASS: dvdcss_open(NULL) returns NULL\n");
} else {
    test_failed++;
    dvdcss_close(h);
}
```

---

## 7. 打包与分发

### 7.1 打包内容
```
libdvdcss-1.5.0-ohos-aarch64.tar.gz
├── lib/
│   ├── libdvdcss.so.2.3.0      # 动态库
│   ├── libdvdcss.so.2          # soname链接
│   ├── libdvdcss.so            # 开发链接
│   ├── libdvdcss.a             # 静态库
│   └── pkgconfig/
│       └── libdvdcss.pc        # pkg-config文件
├── include/
│   └── dvdcss/
│       ├── dvdcss.h
│       ├── dvdcpxm.h
│       └── version.h
└── share/
    └── doc/
        └── libdvdcss/
            ├── AUTHORS
            ├── COPYING
            ├── NEWS
            └── README.md
```

### 7.2 安装脚本示例
```bash
#!/bin/sh
PREFIX=/usr/local

cp -r lib/* $PREFIX/lib/
cp -r include/* $PREFIX/include/
cp -r share/* $PREFIX/share/

ldconfig
```

---

## 8. 常见问题解决

### 8.1 编译问题

**问题**: Meson未安装  
**解决**: `pip install meson ninja`

**问题**: 找不到pkg-config  
**解决**: 安装pkg-config并设置PKG_CONFIG_PATH

**问题**: 符号链接失败  
**解决**: 检查库文件是否正确生成，手动创建符号链接

### 8.2 运行问题

**问题**: 无法打开DVD设备  
**原因**: 权限不足或设备不存在  
**解决**: 检查设备权限，使用正确的设备路径

**问题**: 链接错误  
**原因**: 库路径未设置  
**解决**: 设置LD_LIBRARY_PATH或使用pkg-config

---

## 9. 最佳实践

### 9.1 编译最佳实践
- 使用Meson构建（比Autotools更现代）
- 同时构建静态库和动态库
- 启用调试符号（便于调试）
- 使用pkg-config管理依赖

### 9.2 测试最佳实践
- 测试所有API函数的错误处理
- 验证NULL参数的安全性
- 检查所有导出符号
- 测试编译链接流程

### 9.3 集成最佳实践
- 在实际DVD应用中测试功能
- 与libdvdread配合使用
- 正确处理错误返回值
- 遵守GPL许可证要求

---

## 10. 相关资源

### 10.1 官方资源
- VideoLAN: https://www.videolan.org/
- 源码仓库: https://code.videolan.org/videolan/libdvdcss
- 文档: README.md, NEWS

### 10.2 依赖库
- libdvdread - DVD文件系统读取
- libdvdnav - DVD导航功能
- VLC media player - 完整播放方案

### 10.3 参考文档
- Meson构建系统文档: https://mesonbuild.com/
- OpenHarmony编译指南
- POSIX API文档

---

## 11. 知识总结

### 关键知识点
1. libdvdcss使用Meson构建系统，配置简单
2. 无外部依赖，编译独立完成
3. API设计简洁，错误处理完善
4. 支持动态库和静态库两种形式
5. 平台适配自动检测，无需手动配置

### 编译经验
- Meson比Autotools更适合现代编译环境
- 使用静态库测试更稳定可靠
- 符号验证是功能测试的关键
- pkg-config文件对集成很重要

### 注意事项
- 需要DVD设备才能进行完整功能测试
- GPL许可证有使用限制
- 不同平台的DVD ioctl不同

---

**文档版本**: 1.0  
**生成时间**: 2026-05-15  
**状态**: 完成