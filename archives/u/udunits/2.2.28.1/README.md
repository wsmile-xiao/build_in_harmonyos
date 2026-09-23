# udunits v2.2.28.1 — 鸿蒙预编译包

## 什么是 udunits？

UDUNITS-2 是一个用于物理量单位转换的 C 库和命令行工具。
它支持超过 3000 种单位定义（长度、时间、温度、压力、能量等）。

## 包内容

| 文件 | 说明 |
|------|------|
| `bin/udunits2` | 交互式单位转换程序 |
| `lib/libudunits2.so.0.1.0` | 共享库 (141KB) |
| `lib/libudunits2.so.0` | Soname 链接（实际文件副本，非软链接） |
| `lib/libudunits2.so` | 开发链接（实际文件副本） |
| `lib/libudunits2.a` | 静态库 (243KB) |
| `include/udunits2.h` | 主头文件 |
| `include/converter.h` | 转换器 API 头文件 |
| `include/udunits.h` | 旧版兼容头文件 |
| `share/udunits/udunits2*.xml` | 单位定义数据库 |
| `lib/pkgconfig/udunits2.pc` | pkg-config 文件 |

## 依赖

- **expat** ≥ 2.7.1（共享库依赖）
- **libc**（musl，鸿蒙内核 1.12.0）

## 安装

```bash
# 通过 cmd-pkgs 安装（如可用）
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- udunits

# 或手动解压 tarball 到 ~/usr/local
tar xf udunits-2.2.28.1-ohos-aarch64.tar.gz -C ~/usr/local
```

## 快速使用

```bash
# 交互式单位转换
udunits2 ~/usr/local/share/udunits/udunits2.xml

# 示例转换
# You have: 1 m          → 3.28084 ft
# You have: 273.15 K     → 0 degC
# You have: 1 kg         → 2.20462 lb
# You have: 1 mile       → 1.60934 km
```

## C API 使用

```c
#include <udunits2.h>
#include <converter.h>

ut_system* sys = ut_read_xml("~/usr/local/share/udunits/udunits2.xml");
ut_unit* meter = ut_get_unit_by_name(sys, "meter");
ut_unit* foot = ut_get_unit_by_name(sys, "foot");
cv_converter* conv = ut_get_converter(meter, foot);
double result = cv_convert_double(conv, 1.0);  // 3.28084
```

## 编译信息

- **构建系统**: autotools
- **编译器**: clang 15.0.4（aarch64，musl）
- **配置选项**: `LDFLAGS="-Wl,-rpath,$ORIGIN/../lib" --prefix=$HOME/usr/local`
- **许可证**: MIT

## 已知问题

- HMDFS 文件系统上的共享库软链接（.so、.so.N）无法被 musl 动态链接器解析；
  本包中使用实际文件副本替代软链接。
- 部分单位定义覆盖了前缀单位定义（`-r` 选项会显示数据库警告），
  这是上游已知的兼容性问题，不影响功能。