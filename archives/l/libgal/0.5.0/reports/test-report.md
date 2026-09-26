# libgal 0.5.0 测试报告（OHOS aarch64）

## 环境

- 目标平台：OpenHarmony / HarmonyOS PC，aarch64 (armv8)
- 编译器：clang 15（/data/service/hnp/bin/clang）
- 构建方式：conan 2.29.1 + 上游 autotools（`--host=aarch64-linux-ohos`，静态库）
- 源码：libgal-0.5.0.tar.gz（sha256 0e149ba25a9c7f4d3705c2d9c2e7821d0a751d70adc2effb248b27f62085ad31）

## 上游测试（make check，14 个程序，未修改任何上游测试文件）

| # | 程序 | 通过 | 失败 | 结果 |
|---|------|------|------|------|
| 1 | gal_tdatetime | 71 | 0 | PASS |
| 2 | gal_tvecmat | 231 | 0 | PASS |
| 3 | gal_tprecnut | 620 | 0 | PASS |
| 4 | gal_tearthrot | 15 | 0 | PASS |
| 5 | gal_tephemerides | 1167 | 0 | PASS |
| 6 | gal_tpstrings | 94 | 0 | PASS |
| 7 | gal_tstar | 51 | 0 | PASS |
| 8 | gal_tellipsoids | 91 | 0 | PASS |
| 9 | gal_tmath | 22 | 0 | PASS |
| 10 | gal_tgravity | 48022 | 0 | PASS |
| 11 | gal_tsgp4 | 3146 | 0 | PASS |
| 12 | gal_tref | 86 | 1 | FAIL（见备注 1） |
| 13 | gal_todeint | 25 | 0 | PASS |
| 14 | gal_tkepler | 332 | 0 | PASS |
| **合计** | | **53973** | **1** | **99.998%** |

备注 1：gal_tref 中 gal_c2tpv00a/gal_t2cpv00a 往返一致性断言容差 1e-12（量级 ~4743，约
2 ULP 余量），OHOS aarch64 libm 实测偏差 1.8e-12。在 -O0/-O1/-O2/-O3 与开/关
`-ffp-contract=off` 下结果完全一致，为平台浮点特性而非算法缺陷。

上游测试缺陷修复（不触碰测试文件，均为库源码修复）：

- `gal_vsop87()` j==0 读 `t[-1]` 越界（clang -O3/aarch64 误编译，VSOP87 全部速度分量
  清零 → 上游 549 项失败）；守卫修复后 1167/1167。
- `gal_tledec()` `%5ld` 写 4 字节 int（LP64 结构体破坏，classification/intldesg 清零 →
  上游 2 项失败）；`%5d` 修复后 3146/3146。

## 鸿蒙特有测试（test_package 消费者，9/9 通过）

消费者以 CMake 链接 `libgal::libgal` 静态目标，在 OHOS aarch64 真实编译、链接并执行：

| 断言 | 结果 |
|------|------|
| gal_cal2jd(2000,1,1) 状态码 = 0 | PASS |
| djm0 = 2400000.5 | PASS |
| djm = 51544.0（JD 2451544.5，J2000.0 当天） | PASS |
| gal_cal2jd 坏月（2000,13,1）= -2 | PASS |
| gal_cal2jd 坏日（2000,1,32）= -3 | PASS |
| gal_pdp((1,2,3),(4,5,6)) = 32 | PASS |
| ISS TLE line2 长度 = 69 | PASS |
| gal_tlechksum(ISS TLE line2) = '7' | PASS |
| gal_tlechksum(TLE 格式行) = '1' | PASS |

输出：`GAL_CONSUMER_ASSERTIONS=9/9`、`GAL_CONSUMER_TEST=PASS`。

## 交付物校验

- 包内 `lib/libgal.a` 存在；`include/gal.h`、`gal_const.h` 及各子库头文件齐全
  （include 336 个文件，含 share/doc/libgal/README）。
- 配方对 make-check 日志做逐程序精确校验（计数 + PASS/FAIL 标记），任何回归即失败。
