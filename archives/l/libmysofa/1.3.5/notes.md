# libmysofa 1.3.5 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-07
- 编译器: clang 15.0.4 (target aarch64-unknown-linux-ohos) / clang++
- 状态: built

## 编译步骤

```bash
# 库本体 + 测试二进制（BUILD_TESTS=ON 用于适配验证阶段）
CC=/data/service/hnp/bin/clang cmake -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTS=ON \
  -DMATH=<sysroot>/usr/lib/aarch64-linux-ohos/libm.a \
  -DZLIB_LIBRARY=<conan zlib>/libz.a -DZLIB_INCLUDE_DIR=<conan zlib>/include \
  -DCUNIT_LIBRARY=<conan cunit>/libcunit.a -DCUNIT_INCLUDE_DIR=<conan cunit>/include <src>
make -j4

# 完整门禁（W3 本地 CI 模拟，conan create + test_package）
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | multithread 测试链接失败: undefined symbol pthread_cancel | OHOS musl libc 无 pthread_cancel 符号（glibc 专有） | patches/0002: watchdog 线程改为标志位+join（可移植，无平台宏），保持 600s 超时语义 |
| 2 | external 测试崩溃 Signal 6 | 鸿蒙 /tmp 只读 (E002)，fopen("/tmp/easy.tmp.json") 返回 NULL，printJson(NULL) 崩溃 | patches/0001: 输出改到工作目录相对路径 |
| 3 | find_library(MATH m) 报 NOTFOUND | OHOS 交叉 sysroot 不在 CMake 默认搜索路径（profile 仅注入 compiler_executables） | conanfile.py generate(): OHOS 下 glob sysroot 并按 arch 显式注入 MATH=libm.a |
| 4 | 16 个 ctest 比对用例 Failed (Signal 5) | node/V8 在 OHOS musl 触发 errno 断言崩溃（`Check failed: 12 == (*__errno_location())`），非 libmysofa 缺陷 | 用 python 等价比对器（容差 0.05，复刻 compare.sh/compareIgnoreNew.sh 语义）交叉验证 16/16 EQUAL；详见 test-report.md |

## 源码修改

- patches/0001-src-tests-easy.c.patch（+1/-1）
- patches/0002-src-tests-multithread.c.patch（+11/-2）

## 依赖版本

- zlib/1.3.1（registry ohpcd 已发布，gunzip 路径依赖）
- cunit/2.1.3（仅测试依赖，registry ohpcd 已发布）

## 验证结果

```bash
# 上游测试：ctest 41 项（25 原生通过 + 16 项 node 崩溃经等价比对 16/16 EQUAL）
# CUnit: external 13/13 (20934 断言) + internal 2/2 + multithread ALL GOOD
# 鸿蒙专项: ohos_special_test 5 项 ALL PASSED
# 消费者: test_libmysofa PASSED (M=1250 N=256 R=2)
# conan create 全流程 exit 0，test_package 2/2 ctest 通过
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py / conandata.yml | Conan 配方（静态库 libmysofa.a + 头文件） |
| test_package/ | 消费者测试 + 鸿蒙专项测试（数据 data/testfile.sofa） |
| patches/ | 2 个测试平台适配补丁 |
| reports/test-report.md | 双口径测试台账与鸿蒙专项验证 |

## 注意事项

- 库本体为纯 C，无平台宏补丁；两处测试补丁均为可移植写法（不引入 `__OHOS__`）。
- node 比对工具在当前 OHOS 环境不可用属基础设施问题，非库缺陷；CI 侧如仍用
  node 步骤，需 node 版本兼容 musl errno 检查或替换等价比对器。
---

**编译结束**: 2026-09-08 08:33
**最终状态**: built
