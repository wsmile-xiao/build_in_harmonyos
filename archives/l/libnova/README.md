# libnova

**天文动力学计算库 - Celestial Mechanics, Astrometry and Astrodynamics Library**

## 简介

libnova 是一个用于天文动力学计算的 C 库，提供天体位置计算、轨道预测等功能。它是 INDI (Instrument Neutral Distributed Interface) 协议天文仪器软件的关键依赖。

## 功能

- **Julian Day 计算**: 日期和时间转换
- **太阳位置计算**: 太阳赤道坐标、黄道坐标
- **月球位置计算**: 月球轨道参数、月相
- **行星位置**: VSOP87 行星理论实现
- **恒星时计算**: 地方恒星时、格林尼治恒星时
- **动力学时间**: TDT、TAI 时间转换
- **大气折射**: 大气折射修正
- **视差计算**: 地心坐标转换

## 编译版本

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 0.14.0 | published | 2026-06-08 | 当前版本 |

## 依赖关系

**作为依赖被使用**:
- libindi: INDI 协议天文仪器库 (REQUIRED 依赖)

## 安装方法

使用预编译包安装:
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libnova 0.14.0
```

## 使用示例

```c
#include <libnova/julian_day.h>
#include <libnova/solar.h>

int main() {
    struct ln_date date;
    date.years = 2026;
    date.months = 6;
    date.days = 8;

    double jd = ln_get_julian_day(&date);
    printf("Julian Day: %.6f\n", jd);

    struct ln_equ_posn sun_pos;
    ln_get_solar_equ_coords(jd, &sun_pos);
    printf("Sun RA: %.2f, Dec: %.2f\n", sun_pos.ra, sun_pos.dec);

    return 0;
}
```

编译:
```bash
clang -o my_program my_program.c \
    -I$PREFIX/include \
    -L$PREFIX/lib \
    -lnova \
    -Wl,-rpath,$PREFIX/lib
```

## 平台适配说明

### E011 HMDFS 权限问题

libnova 使用 autotools 构建系统，在 HarmonyOS HMDFS 文件系统上需要修复 configure 脚本:

```bash
sed -i 's/umask 077/umask 022/g' configure
./configure --prefix=$DEFAULT_PREFIX
```

## 许可证

LGPL-2.1

## 项目主页

- GitHub: https://github.com/JohannesBuchner/libnova
- 原项目: http://libnova.sourceforge.net/

## 相关软件

- libindi: INDI 协议天文仪器库
- Stellarium: 天文软件（使用 libnova）
- KStars: KDE 天文软件（使用 libnova）