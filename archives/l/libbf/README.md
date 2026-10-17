# libbf — OpenHarmony 编译记录

## 基本信息
- 软件: libbf (Fabrice Bellard 任意精度浮点小库, MIT)
- 上游: https://bellard.org/libbf/
- 构建系统: makefile
- 产物: 静态库 libbf.a + 公开头文件 libbf.h

## 版本
- 2021.03.27: 源码取自同日期 quickjs 捆绑包内同一 libbf (独立历史包已下架),
  上游 test_bignum.js 回归 + test_package 5 项消费者断言。
