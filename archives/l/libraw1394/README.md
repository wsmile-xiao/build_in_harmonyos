# libraw1394 2.1.2

## 简介
libraw1394 是 IEEE 1394 (FireWire) 设备访问库，提供对 FireWire 设备的底层访问接口。

## 版本信息
- 版本: 2.1.2
- 发布日期: 2016-04-03
- 构建系统: autotools

## 编译状态
✅ 编译成功

## 依赖
- 无外部依赖

## 安装
使用预编译包安装:
```bash
curl -fsSL <URL>/libraw1394-2.1.2-ohos-aarch64.tar.gz | tar xzf -
PREFIX=/storage/Users/currentUser/usr/local
cp -r lib $PREFIX/
cp -r include $PREFIX/
```

或使用 install.sh:
```bash
PREFIX=/storage/Users/currentUser/usr/local sh install.sh
```

## 库文件
- `lib/libraw1394.a` - 静态库
- `lib/libraw1394.so` - 共享库

## 头文件
- `raw1394.h` - 主 API 头文件
- `fw.h` - FireWire 内核接口
- `ieee1394.h` - IEEE 1394 常量定义
- `csr.h` - CSR (Control and Status Register) 定义
- `firewire-cdev.h` - FireWire 内核设备接口
- `firewire-constants.h` - FireWire 常量

## 使用示例
```c
#include <raw1394.h>

int main() {
    raw1394handle_t handle = raw1394_new_handle();
    if (!handle) {
        fprintf(stderr, "无法打开 FireWire 设备\n");
        return 1;
    }
    
    int num_ports = raw1394_get_port_info(handle, NULL, 0);
    printf("检测到 %d 个 FireWire 端口\n", num_ports);
    
    raw1394_destroy_handle(handle);
    return 0;
}
```

编译:
```bash
clang -o test test.c -lraw1394
```

## 编译过程中的关键问题

### E007: config.guess 无法识别 HarmonyOS
**症状**: `config.guess: unable to guess system type`

**解决方案**: 修改 config.guess 添加 HarmonyOS 检测分支，输出 `aarch64-unknown-linux-ohos`

### HMDFS 文件系统限制
**症状**: `config.status: could not setup config files machinery`

**解决方案**: 手动创建 config.h 并直接编译源码，绕过 configure 的临时文件创建

## 注意事项
- 需要内核支持 FireWire 设备 (`/dev/fw*`)
- HarmonyOS 目前没有 FireWire 设备支持，此库主要用于交叉编译或开发环境