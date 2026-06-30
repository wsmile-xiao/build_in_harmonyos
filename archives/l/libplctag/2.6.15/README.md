# libplctag 2.6.15 — HarmonyOS (OpenHarmony) 预编译包

## 软件简介
libplctag 是一个用于通过以太网访问 Allen-Bradley PLC 数据的便携式简单 API 库。
支持 AB PLC（ControlLogix/CompactLogix/Micro800）和 Modbus 协议。

- **官方主页**: https://github.com/libplctag/libplctag
- **许可证**: LGPL-2.0-or-later OR MPL-2.0
- **版本**: 2.6.15

## 预编译包信息
- **目标架构**: ohos-aarch64 (HarmonyOS/OpenHarmony)
- **编译器**: clang 15.0.4
- **构建系统**: cmake (MinSizeRel)
- **包文件**: `libplctag-2.6.15-ohos-aarch64.tar.gz`

## 包内容
| 路径 | 说明 |
|------|------|
| lib/libplctag.so.2.6.15 | 共享库（465KB） |
| lib/libplctag.so.2.6 | 版本符号链接 |
| lib/libplctag.so | 开发符号链接 |
| lib/libplctag_static.a | 静态库（1067KB） |
| lib/pkgconfig/libplctag.pc | pkg-config 文件 |
| include/libplctag.h | 头文件 |
| bin/tag_rw2 | PLC 标签读写工具 |
| bin/modbus_server | Modbus 服务器（POC） |

## 使用方法

### 安装
```bash
# 解压到目标目录
tar xf libplctag-2.6.15-ohos-aarch64.tar.gz -C /usr/local
```

### 动态链接
```bash
# 使用 pkg-config
export PKG_CONFIG_PATH=/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
clang `pkg-config --cflags --libs libplctag` myapp.c -o myapp
```

### 静态链接
```bash
clang -I/usr/local/include myapp.c /usr/local/lib/libplctag_static.a -lpthread -lm -o myapp
```

### C API 示例
```c
#include <libplctag.h>

int main(void) {
    // 检查库版本
    int rc = plc_tag_check_lib_version(2, 6, 15);
    if (rc != PLCTAG_STATUS_OK) {
        fprintf(stderr, "版本不匹配: %s\n", plc_tag_decode_error(rc));
        return 1;
    }

    // 创建PLC标签
    int32_t tag = plc_tag_create(
        "protocol=ab_eip&gateway=192.168.1.1&path=1,0&name=MyTag&elem_size=4&elem_count=1",
        5000);

    if (tag < 0) {
        fprintf(stderr, "创建标签失败: %s\n", plc_tag_decode_error(tag));
        return 1;
    }

    // 读取数据
    rc = plc_tag_read(tag, 5000);
    if (rc == PLCTAG_STATUS_OK) {
        int32_t value = plc_tag_get_int32(tag, 0);
        printf("标签值: %d\n", value);
    }

    plc_tag_destroy(tag);
    plc_tag_shutdown();
    return 0;
}
```

## HarmonyOS 适配说明

本预编译包已针对 HarmonyOS (OpenHarmony) 平台进行适配，主要修改包括：

1. **平台检测**: 添加 `CMAKE_SYSTEM_NAME=Linux` 使 cmake 识别 HarmonyOS 为 UNIX 兼容平台
2. **libatomic**: aarch64 平台 clang 内建支持原子操作，无需链接 libatomic
3. **pthread_cancel**: HarmonyOS 不支持 pthread_cancel，替换为 pthread_kill（同 Android 方案）
4. **编译器兼容**: 修复 clang C99 严格模式下的 switch/case 变量声明问题

详见 `patches/` 目录下的5个补丁文件。

## 依赖
- 系统库: libc.so, pthread, libm（HarmonyOS 系统自带）
- 无三方库依赖
