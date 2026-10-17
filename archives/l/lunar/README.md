# lunar

`lunar` 是 Fung F. Lee 与 Ricky Yeung 的经典农历换算工具（GPL-2.0-or-later，
1988 年首发，2001-10-28 发布 2.2 版），在**公历（Gregorian Solar Calendar）**
与**中国农历（Chinese Lunar Calendar，北京时间）**之间双向换算，并给出干支、
生肖与八字。

## Versions

| Version | Status | Assertions |
| --- | --- | --- |
| 2.2 | built | 67 |

Homepage: https://tracker.debian.org/pkg/lunar

## 功能

- **公历 → 农历**：`lunar year month day [hour]`
- **农历 → 公历**：`lunar -i year month day [hour]`，`-l` 表示闰月（run-yue）
- **生肖（ShengXiao）**：如 Rabbit / Dragon / Snake
- **干支（GanZhi）**：年/月/日/时四柱，同时给出 GanZhi Order 与 JiaZi Cycle 两套编号
- **八字（BaZi）**：按 "Four Column Calculation" 输出
- **`-h`**：汉字输出（GB 编码）
- **`-b`**：特殊 bitmap 字形输出（需要 `lunar.bitmap` 数据文件）

## 使用方法

```bash
# 公历 2000-01-01 → 农历（1999 己卯年十一月廿五，属兔）
lunar 2000 1 1

# 农历 2000 年正月初一 → 公历（2000-02-05）
lunar -i 2000 1 1

# 2023 年闰二月十五 → 公历
lunar -i -l 2023 2 15

# 汉字输出
lunar -h 2000 1 1

# bitmap 字形输出（需在含 lunar.bitmap 的目录下执行）
cd "$(conan cache path lunar/2.2)/share/lunar" && lunar -b 2000 1 1
```

## 支持区间

约 150 年：公历 **1900-01-31**（农历 1900 正月初一）至 **2049-12-31**
（农历 2049 十二月初七）。越界时以非 0 退出码报 `Year/Month/Day out of range.`。

## OHOS 适配

| 项目 | 说明 |
| --- | --- |
| 目标 | `aarch64-linux-ohos`（musl）|
| 源码 | 单 `.c` + `tables.h`，仅依赖 `stdio.h` / `string.h` |
| 外部库 | 无 |
| patch | 无（musl 全支持）|
| 构建 | 直驱 clang：`clang -O2 -w -std=gnu99 -o lunar lunar.c` |
| 产物 | `bin/lunar`（约 33 KB）|
| 数据 | `share/lunar/lunar.bitmap`（`-b` 用）、`share/man/man1/lunar.1` |

上游代码是 2001 年的 K&R 风格函数定义（`int main(argc, argv)` + 分离参数声明），
clang 15 的默认 `gnu17` 依然接受；上游 `Makefile` 只有 `lunar:` 与 `clean:`
两个目标且用裸 `cc`、`rm *.o`，在交叉编译环境里都不可靠，因此 `build()`
直接调用 `clang`。

### 运行时说明

`lunar` 是纯计算程序，除 `-b` 需要 `lunar.bitmap` 外不触达任何设备、
网络或特权接口，因此在消费级 HarmonyOS PC 上可无条件运行。
`-b` 用例通过 `share/lunar` 数据目录执行（`cd <dir> && lunar -b ...`），
因为上游用相对路径 `"lunar.bitmap"` 打开该文件。

## 测试

上游**不含任何测试套件**（无 `make check` 目标、无测试源文件、无对照表数据）。
`test_package/test_lunar.c` 提供 67 条消费者断言，覆盖：

1. 公历→农历基准换算（含区间下界 1900-01-31、上界 2049-12-31、两个春节）
2. 农历→公历反查
3. 闰月（2023 闰二月）
4. 农历日起于 23:00 的约定（SC 1991.2.15.23 与 SC 1991.2.16.0 同为 LC 1991.1.2）
5. `-h` 汉字段输出
6. 三类越界错误（月/日/年）与三类用法错误，均须非 0 退出码
7. **往返一致性属性测试**：12 个跨全区间采样点做 solar→lunar→solar 必须回到原点
8. `-b` bitmap 字形输出

判据全程用 `popen` 内存管道直读子进程输出，**不写任何临时文件**——OHOS 上
`/tmp` 是只读文件系统，任何"先重定向落盘再 grep"的写法都会与被测程序无关地失败。
