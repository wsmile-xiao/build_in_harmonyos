# exempi 2.6.6 - OpenHarmony 预编译包

## 简介

exempi 是 XMP (Extensible Metadata Platform) 元数据的 C/C++ 库和命令行工具，基于 Adobe XMP SDK 开发。本包为 OpenHarmony (aarch64-unknown-linux-ohos) 平台的预编译版本。

## 版本信息

- **软件版本**: 2.6.6
- **构建日期**: 2026-05-28
- **目标平台**: aarch64-unknown-linux-ohos (OpenHarmony ARM64)
- **构建系统**: autotools
- **编译器**: clang/clang++ (OHOS SDK 26.0.0.18)

## 依赖

- expat >= 2.7.1 (XML 解析库)
- musl libc (OHOS 系统标准 C 库)

## 安装内容

| 文件 | 说明 |
|------|------|
| `bin/exempi` | XMP 元数据命令行工具 |
| `lib/libexempi.so.8.1.6` | 共享库 (soname: libexempi.so.8) |
| `lib/libexempi.a` | 静态库 |
| `include/exempi-2.0/exempi/xmp.h` | C API 头文件 |
| `include/exempi-2.0/exempi/xmp++.hpp` | C++ API 头文件 |
| `include/exempi-2.0/exempi/xmpconsts.h` | 常量定义 |
| `include/exempi-2.0/exempi/xmperrors.h` | 错误码定义 |
| `lib/pkgconfig/exempi-2.0.pc` | pkg-config 文件 |

## 使用方法

### 命令行

```bash
# 查看 XMP 元数据
exempi -x photo.jpg

# 获取特定属性
exempi -g dc:title photo.jpg

# 设置属性
exempi -w -s dc:title -v "新标题" photo.jpg
```

### C 语言 API

```c
#include <exempi/xmp.h>

xmp_init();
XmpPtr xmp = xmp_new_empty();
xmp_set_property(xmp, "http://purl.org/dc/elements/1.1/", "title", "标题", 0);
// ... 使用 XMP API ...
xmp_free(xmp);
xmp_terminate();
```

### pkg-config

```bash
pkg-config --cflags exempi-2.0   # 编译选项
pkg-config --libs exempi-2.0     # 链接选项
```

## 已知限制

1. 不支持 `--version` 标志（使用无参数运行查看版本号）
2. 单元测试已禁用（boost 库在 OHOS 平台不可用）
3. HMDFS 文件系统需要修补 configure 脚本才能正常编译

## 补丁说明

本包使用了 3 个平台适配补丁：

1. **config.guess**: 添加 __OHOS__ libc 检测和 HarmonyOS 系统标识
2. **config.sub**: 修复 ohos-linux 三元组支持
3. **configure**: 将 mktemp -d 替换为 mkdir -p (HMDFS 文件系统兼容性)