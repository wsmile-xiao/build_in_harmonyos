# boost1.84-system 1.84.0 适配笔记

## 编译环境
- 构建系统: custom（手动编译单翻译单元，绕过 b2）
- 编译日期: 2026-09-05
- 编译器: clang 15 (OHOS SDK /data/service/hnp/bin/clang++)
- 状态: built

## 组件定位
Boost 1.84.0 组件拆分包之一：**Boost.System**（boost::system::error_code /
error_condition / system_error）。供下游以 `boost1.84-system/1.84.0` 精确
依赖该组件，不必拉取 boost/1.84.0 聚合包（聚合包只含 filesystem/regex/
program_options/iostreams 四个编译库）。

## 编译步骤
1. 下载官方源码 boost_1_84_0.tar.gz（sha256 a5800f40...5724，与 boost/1.84.0 同源）
2. 应用补丁 0001-ohos-pthread-cancel-fix.patch：
   boost/core/detail/sp_thread_sleep.hpp 增加 BOOST_SP_NO_PTHREAD_SETCANCELSTATE
   特性宏守卫（OHOS musl 无 pthread_setcancelstate）
3. 手动编译唯一翻译单元（B2 在 OHOS 不兼容，E068）：
   ```
   clang++ -std=c++17 -stdlib=libc++ -fPIC -O2 -DNDEBUG \
     -DBOOST_ALL_NO_LIB -DBOOST_SYSTEM_NO_DEPRECATED -DBOOST_SYSTEM_SOURCE \
     -I<boost_root> -c libs/system/src/error_code.cpp -o error_code.o
   llvm-ar rcs libboost_system.a error_code.o
   ```
4. package(): 复制全量 boost/ 头文件 + libboost_system.a

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | b2 构建失败 | Boost.Build SHELL 执行机制与 OHOS shell 不兼容（E068） | 手动编译 libs/system/src/error_code.cpp（该库仅此一个编译单元） |
| 2 | sp_thread_sleep.hpp 编译报 pthread_setcancelstate 未声明 | OHOS musl 不实现该 POSIX 取消点 API | 复用 boost/1.84.0 已验证补丁：特性宏 BOOST_SP_NO_PTHREAD_SETCANCELSTATE 守卫（R8 合规，非平台宏） |
| 3 | error_code_test 2 处断言失败 | 上游断言 glibc strerror 文本（"Unknown error"），OHOS musl 对未知 errno 返回 "No error information" | 平台 libc 行为差异，记录豁免说明，不修改上游测试 |

## 源码修改
- patches/0001-ohos-pthread-cancel-fix.patch（与 boost/1.84.0 同一补丁，portability 类型）

## 依赖版本
- 无外部 conan 依赖（error_code.cpp 仅依赖 boost 头自身 + libc）

## 验证结果

```bash
# 上游测试（94 项，绕过 b2 手动驱动）
clang++ <test>.cpp -L. -lboost_system && ./a.out
# 结果: 93 passed / 1 failed (error_code_test, strerror 文本差异, 详见 MANIFEST.yml)

# test_package（conan create 内执行）
# boost::system::error_code 构造/值/类别/消息 + errc 比较 + system_category
# + system_error 抛出捕获回环 + std::error_code 互操作 → PASS
```

## 注意事项
- package_type = static-library；R26 系统同名检查通过（libboost_system 非
  OHOS 系统库名）
- cmake_file_name 用 boost_system_pkg（避免与聚合 boost 包的 Boost config
  冲突），组件 cmake target 为 boost_system_pkg::system
- 头文件全量安装（~244MB 源码树，含 include/boost），下游无需再装 boost 头
---

**编译结束**: 2026-09-05 17:41
**最终状态**: built
