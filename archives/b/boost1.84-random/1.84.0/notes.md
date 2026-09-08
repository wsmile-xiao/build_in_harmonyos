# boost1.84-random 1.84.0 编译笔记

## 编译开始时间
2026-09-05 14:05

## 编译系统
手动编译（Boost.Build 不可用，同底稿 archives/b/boost/1.84.0 方案）

## 源码
- URL：https://downloads.sourceforge.net/project/boost/boost/1.84.0/boost_1_84_0.tar.gz
- SHA256：a5800f405508f5df8114558ca9855d2640a2de8f0445f051fa1c7c3383045724
- 与元包 boost/1.84.0 完全同源（组件独立裁剪打法）

## 适配方案（继承底稿已验证结论）

底稿 archives/b/boost/1.84.0 已证明 b2 不可用（E068），手动编译是可行方案。
本组件包按同样打法只编译 random：

- libs/random/src/random_device.cpp（上游唯一需编译的源文件）

编译标志：
```
-std=c++17 -stdlib=libc++ -O2 -DNDEBUG -fPIC -I<boost_root>
-DBOOST_ALL_NO_LIB -DBOOST_SYSTEM_NO_DEPRECATED
-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE   # 配合 0001 补丁（OHOS musl 无 pthread_setcancelstate）
```

random_device 在非 Windows 平台自动选择 POSIX 后端（open/read/close 读
/dev/urandom），OHOS musl 兼容，无需源码修改。它 include 了
boost/system 头文件，但 system 自 1.69 起为 header-only，无需额外依赖
（b2 --with-random 不需要链接 boost_system，无 conan requirements）。

## 上游测试（2026-09-05 实测）

b2 不可用 → 手动编译测试源文件，链接 libboost_random.a 直接运行：

| 测试 | 断言/用例数 | 结果 |
|---|---|---|
| test_random_device.cpp | 6 断言组（entropy/范围/generate） | PASS |
| test_mt19937.cpp | 15 用例（含验证值 4123659995U） | PASS |
| test_mt19937_64.cpp | 15 用例（含验证值 9981545732273789042） | PASS |
| random_demo.cpp（example） | 演示程序 | PASS |

TOTAL 4: 4 passed / 0 failed

### mt19937 系列测试的处理说明

上游 test_mt19937.cpp / test_mt19937_64.cpp include "test_generator.ipp"，
后者用 linked 版 <boost/test/unit_test.hpp>，b2 通过链接
boost_unit_test_framework 提供实现。本配方未编译 test 库（不属于 random
组件范围），改用 <boost/test/included/unit_test.hpp> 单头全实现：
- BOOST_RANDOM_URNG / VALIDATION_VALUE 等宏与上游测试文件逐字一致
- 断言与验证值完全不变，仅 unit_test 框架的实现方式从 linked 换为 included
- 曾实测：SEED_WORDS 抄错（312 vs 上游 624）时测试立即失败——证明断言真实有效

## 遇到的问题

无平台障碍。boost::system 头文件在 libc++ 下编译正常。

## 运行时注意

本机运行测试二进制需要 LD_LIBRARY_PATH 指向 OHOS SDK 的 libc++_shared.so
（conan 构建内测试与 test_package 均已用 clang++ -print-file-name 动态定位自动处理）。
---

**编译结束**: 2026-09-05 19:10
**最终状态**: built
