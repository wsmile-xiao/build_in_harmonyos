# libinput 1.26.0 编译笔记

## 编译日期
2026-05-30

## 编译环境
- OpenHarmony
- TMPDIR=/data/storage/el2/base/cache
- 编译器: clang

## 成功编译 ✅

### 1. 创建 libudev stub
由于 OpenHarmony 没有 libudev，创建了完整的 stub：
- `libudev.so.0` (31KB) - stub 库
- `libudev.h` - 头文件（包含所有必要函数声明和宏）

### 2. 修复的 OpenHarmony 平台兼容性问题

| 问题 | 位置 | 解决方案 |
|------|------|----------|
| dev_t/useconds_t 未定义 | libudev.h | 添加类型定义 |
| udev_device_get_parent 缺失 | libudev stub | 添加 stub 函数 |
| udev_list_entry_foreach 缺失 | libudev.h | 添加宏定义 |
| rindex 未定义 | src/util-strings.c:249 | 替换为 strrchr |
| program_invocation_short_name | tools/ptraccel-debug.c:176 | 硬编码为 "ptraccel-debug" |
| program_invocation_short_name | tools/libinput-record.c:2583-2587 | 硬编码为 "libinput-record" |
| git describe 失败 | meson build | 手动创建 libinput-git-version.h |

### 3. meson 配置选项
```bash
meson setup build --prefix=$PREFIX \
  -Dlibwacom=false \
  -Ddebug-gui=false \
  -Dtests=false \
  -Ddocumentation=false
```

## 编译产物

| 文件 | 大小 | 说明 |
|------|------|------|
| libinput.so.10.13.0 | 1.2M | 核心库 |
| libinput | 166K | 主工具 |
| libinput-debug-events | 232K | 调试工具 |
| libinput-list-devices | 187K | 设备列表工具 |
| libinput-record | 281K | 录制工具 |
| libinput-quirks | 174K | quirks 管理 |
| libinput-analyze | 166K | 分析工具 |
| libinput-measure | 166K | 测量工具 |
| libinput-test | 166K | 测试工具 |

## 预编译包
- libinput-1.26.0-ohos-aarch64.tar.gz (3.8M)

## 知识沉淀
- OpenHarmony libc 缺少 program_invocation_short_name（glibc 特性）
- rindex 函数在 OpenHarmony 上不可用，需要用 strrchr 替代
- libudev 是 libinput 的硬依赖，需要 stub 或 eudev