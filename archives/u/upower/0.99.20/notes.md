# UPower 0.99.20 编译笔记

## 编译日期
2026-05-28

## 编译环境
- 系统: HarmonyOS
- 编译器: clang 15.0.4
- 构建系统: meson 1.11.1 + ninja 1.13.1

## 依赖
- glib-2.0 2.88.0 ✅
- gobject-2.0 2.88.0 ✅
- gio-2.0 2.88.0 ✅
- gio-unix-2.0 2.88.0 ✅
- gudev-1.0 238 ✅ (手动编译)
- udev 251 ✅ (系统自带 eudev)

## 关键问题

### 1. 缺少 gudev-1.0 依赖
- **问题**: upower 需要 gudev-1.0 >= 235，但没有预编译包
- **解决**: 手动编译 libgudev-238
  - 源代码: https://github.com/GNOME/libgudev/archive/refs/tags/238.tar.gz
  - 构建系统: meson

### 2. GLib 静态库链接冲突
- **问题**: GLib 编译为静态库，依赖 libintl.a 中的 g_libintl_* 符号，但运行时 libintl.so.8 是标准 gettext 库，不包含这些符号
- **解决**:
  1. 从 libintl.a 创建 libintl_glib.so 动态库
     ```bash
     clang -shared -o libintl_glib.so -Wl,--whole-archive libintl.a -Wl,--no-whole-archive
     ```
  2. 所有依赖 GLib 静态库的共享库都链接 libintl_glib.so

### 3. lld 链接器 --no-allow-shlib-undefined 检查
- **问题**: lld 默认严格检查共享库的未定义符号
- **解决**: 使用 --allow-shlib-undefined 或确保所有符号都正确链接

## 构建配置
```bash
meson setup build src --prefix=$HOME/usr/local --libdir=lib --buildtype=release \
  -Dgtk-doc=false -Dman=false -Dintrospection=disabled -Didevice=disabled \
  -Dsystemdsystemunitdir=no -Dos_backend=linux
```

## 手动链接命令
由于 meson 自动链接失败，需要手动调整链接顺序：
```bash
# libupower-glib
clang -o libupower-glib/libupower-glib.so.3.1.0 ... libintl_glib.so

# upowerd
clang -o src/upowerd ... libintl_glib.so --allow-shlib-undefined

# upower 工具
clang -o tools/upower ... libintl_glib.so
```

## 产物
- bin/upower (27KB)
- libexec/upowerd (383KB)
- lib/libupower-glib.so.3.1.0 (11.3MB)

## 验证
```bash
~/usr/local/bin/upower --help
# 由于没有运行 upowerd 守护进程，功能验证需要启动守护进程
```

## 功能测试结果 (2026-05-28)

### 命令行工具 ✅
- `upower --help`: 正常显示帮助信息
- `upower -e`: 无守护进程时正确报告错误
- 参数解析: 所有选项功能正常

### 共享库 API ✅
- 符号导出: 45+ API 符号完整（up_client_new, up_device_new 等）
- 头文件: 9 个头文件完整可用
- 依赖库: libpcre2-8, libffi, libintl_glib 已打包

### 守护进程 ⚠️
- `upowerd --help`: 参数解析正常
- 启动失败原因:
  1. 缺少 UPower.conf 配置文件
  2. D-Bus 服务未运行（HarmonyOS 系统限制）
  3. 系统缺少 `/sys/class/power_supply` 电源设备目录
- 结论: 编译正确，需系统级服务支持

### 预编译包 ✅
- 文件结构: 22 个文件完整
- 外部依赖: 已包含 libpcre2-8.so.0, libffi.so.8
- 测试报告: reports/test-report.md

### 缺失项修复 (2026-05-28)

**已修复并添加到预编译包**:
1. `etc/UPower/UPower.conf` - 守护进程配置文件 ✅
2. `share/dbus-1/system-services/org.freedesktop.UPower.service` - D-Bus 服务文件 ✅
3. `share/dbus-1/interfaces/org.freedesktop.UPower*.xml` - 3 个接口定义文件 ✅
4. `lib/udev/rules.d/95-upower*.rules` - 2 个 udev 规则文件 ✅
5. `lib/pkgconfig/upower-glib.pc` - pkg-config 文件 ✅

**pkg-config 测试**:
```bash
pkg-config --cflags upower-glib    # 正常返回编译标志
pkg-config --libs upower-glib      # 正常返回链接标志
pkg-config --modversion upower-glib  # 返回 0.99.20
```

### 系统限制（不可修复）
- D-Bus 服务: HarmonyOS 缺少系统级 D-Bus 守护进程
- 电源设备: `/sys/class/power_supply` 目录不存在
- udev 支持: 需要 udev 守护进程配合

## 知识沉淀建议
- E{N}: GLib 静态库 + gettext 动态库链接冲突
  - 触发条件: GLib 编译为静态库
  - 解决方案: 从 libintl.a 创建包含 g_libintl_* 符号的动态库
---

**编译结束**: 2026-05-28 15:37
**最终状态**: built
