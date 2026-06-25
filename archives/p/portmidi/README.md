# PortMidi

## 简介

PortMidi 是一个跨平台的实时 MIDI I/O 库，提供了统一的 API 用于在不同操作系统上进行 MIDI 设备的输入输出操作。

## 版本信息

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| 2.0.8 | built | 2026-05-19 |

## HarmonyOS 编译说明

PortMidi 在 HarmonyOS 上使用 PMNULL 模式编译，因为 HarmonyOS 缺少 ALSA 库（Linux 标准音频/MIDI 驱动）。

### PMNULL 模式说明

- PortMidi 将无法检测或使用 MIDI 设备
- API 函数仍然可用，但会返回"无设备"状态
- 适合作为其他软件的依赖库，但不支持实际 MIDI 操作

### 补丁说明

编译时应用了一个补丁，用于支持 HarmonyOS：
- 补丁文件: `0001-CMakeLists.txt.patch`
- 类型: 平台兼容性补丁
- 内容: 添加 HarmonyOS 检测，将其视为 UNIX 系统处理

## 安装

### 预编译包

```bash
# 解压预编译包
tar -xzf portmidi-2.0.8-ohos-aarch64.tar.gz -C /usr/local
```

### 安装后验证

```bash
# 检查库文件
ls -l /usr/local/lib/libportmidi.so

# 使用 pkg-config 查询
pkg-config --cflags --libs portmidi
```

## 使用示例

```c
#include <portmidi.h>

int main() {
    // 初始化 PortMidi
    Pm_Initialize();
    
    // PMNULL 模式下会返回无设备
    int count = Pm_CountDevices();
    printf("MIDI devices: %d\n", count);
    
    // 清理
    Pm_Terminate();
    return 0;
}
```

## 依赖

无额外依赖（使用 PMNULL 模式）

## 文件结构

- `lib/libportmidi.so` - 主共享库
- `include/portmidi.h` - 主头文件
- `include/pmutil.h` - 工具函数头文件
- `include/porttime.h` - 时间相关头文件
- `lib/pkgconfig/portmidi.pc` - pkg-config 配置
- `lib/cmake/PortMidi/` - CMake 配置文件

## 参考

- 官方网站: https://github.com/PortMidi/portmidi
- 文档: https://github.com/PortMidi/portmidi/blob/main/README.md