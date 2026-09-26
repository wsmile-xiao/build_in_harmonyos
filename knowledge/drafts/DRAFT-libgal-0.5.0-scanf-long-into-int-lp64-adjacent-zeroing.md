# DRAFT: sscanf %ld 写 int 成员——LP64 8 字节存储静默清零结构体相邻字段（libgal 0.5.0 TLE 解码实例）

- **草稿 ID**: DRAFT-libgal-0.5.0-scanf-long-into-int-lp64-adjacent-zeroing
- **关联 PR**: #11135（`feat/libgal-0.5.0`，路径 A+B 原子交付）
- **来源库**: libgal 0.5.0（General Astrodynamics Library；GPL-2.0-or-later；autotools）
- **环境**: OHOS PC aarch64（musl，clang 15，`-O3` 与 `-O0` 行为一致）
- **状态**: 草稿（待主编 promote 为正式 E 条目）

## 1. 触发实例

libgal 上游 sgp4 测试（gal_tsgp4）在 OHOS aarch64 上 2 项失败，且失败模式很"怪"：
`gal_tledec` 返回 GAL_SUCCESS（成功路径），`satnum=25107`、`epochyr=1998`、`bstar=-0.27359e-2`
等**被解析字段与后续字段全部正确**，唯独结构体里紧跟 satnum 的两个字段恒为空：

```
Test gal_tledec classification 0 failed.
Expected value: U  Actual value: (空)
Test gal_tledec intldesg 0 failed.
Expected value: [97082D ]  Actual value: []
```

## 2. 根因：scanf 转换说明符与目标字段类型不符（LP64）

`sgp4/gal_tledec.c` 解码 TLE 卡 2：

```c
sscanf ( card2, "%2d %5ld %9lf %9lf %8lf %9lf %9lf %11lf %5d %1d",
         &cardnumb, &tle->satnum, ... );
```

`gal_tle_t` 布局：`int satnum`（offset 0）、`char classification`（offset 4）、
`char intldesg[10]`（offset 5）。**LP64 上 `%ld` 无条件写 8 字节**：低 4 字节 =
25107（"正确"），高 4 字节 = 0 —— 恰好把 `classification` 和 `intldesg[0..2]`
清零。glibc/musl 行为一致：这不是 libc 差异，是类型不匹配的 UB + LP64 数据模型
（ILP32 平台不炸，所以 2009 年的上游在 32 位时代从未暴露）。

修复（`patches/0003-tledec-scanf-long.patch`，一行）：

```diff
-  sscanf ( card2, "%2d %5ld %9lf %9lf %8lf %9lf %9lf %11lf %5d %1d",
+  sscanf ( card2, "%2d %5d %9lf %9lf %8lf %9lf %9lf %11lf %5d %1d",
```

修复后 sgp4 测试 3146/3146，`classification='U'`、`intldesg='97082D '` 与上游参考一致。

## 3. 判定特征（为什么是"相邻成员清零"而不是"解析失败"）

1. 被解析成员自身值正确（低 4 字节有效）。
2. 只有紧跟其后的相邻成员被清零/清空，更后面的成员由各自的正确写入覆盖。
3. -O0 与 -O3 行为完全一致（排除优化器 UB 类）。
4. 插桩 sscanf 前后对比：sscanf 前字段完好，sscanf 后相邻字段被清——直接锁定。

## 4. 适用面

全部用 scanf 家族解析定长卡/记录格式的 32 位时代 C 库：TLE/航天星历卡、GRIB/气象卡、
NMEA、ham 无线电电报格式；检索特征是格式串中 `%ld/%lx/%lo` 与 `&int` 成员混排。
与 j==0 越界 UB（DRAFT-libgal-0.5.0-vsop87-j0-oob-ub-optimizer-exploited）互为对照组：
那条随优化级变化，本条与优化级无关、与数据模型（ILP32/LP64）相关。

## 5. 修复原则

- 首选：转换说明符对齐被写变量声明类型（`%5ld`→`%5d`），一行、即上游意图。
- 禁止：把 `int` 成员改成 `long`（改变 ABI/结构体布局，殃及所有消费者）。
- 格式串需同时服务多数据模型时，用 `inttypes.h`（`"%" SCNd32`）或分平台宏，不要保留"碰巧能跑"的宽度失配。
- 排查顺序建议：先插桩确认"sscanf 前完好/sscanf 后被清"，再全文核对格式串每一项与实参类型的宽度匹配。
