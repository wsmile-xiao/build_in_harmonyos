# blosc2 3.2.3 HarmonyOS PC 适配笔记

## 任务与源码

- 任务：#6027
- 分支：feat/blosc2-3.2.3
- 上游：https://github.com/Blosc/c-blosc2
- 上游版本：3.2.3
- 构建系统：CMake；源码主语言 C，lang-preflight cpp/c 兼容通过
- 依赖：无 Conan 运行时依赖；CMake FetchContent 获取 LZ4 1.10.0、zlib-ng 2.3.3、ZSTD 1.5.7

## 首次真实构建错误与修复

第一条真实错误是内置 ZSTD 1.5.7 lib/dictBuilder/cover.c 的 undefined symbol qsort_r。OHOS/musl 不提供 GNU qsort_r；E531 与 c-blosc2/2.23.1 先例提供 C90 qsort 回退。3.2.3 使用 FetchContent，因此增加 CMake PATCH_COMMAND 在解包后应用 qsort 补丁，不捎带 ZSTD 源码。

## 上游测试账本

| 维度 | 数量 | 证据 |
|---|---:|---|
| CTest 注册实例（未适配源码） | 1195 | ctest -N |
| C 源测试目标 + compat 数据源文件 | 140 | 111 个测试 C 源/生成器 + 29 个 .cdata |
| CUTEST 原子测试声明 | 47 | CUTEST_TEST_TEST 宏统计 |
| 首轮执行/通过/失败 | 1195/1194/1 | 唯一失败 test_stdio_validation |
| 最终 OHOS 执行/通过/跳过 | 1194/1194/1 | 明确禁用 tmpfile 环境受限测试 |

首轮失败为 tmpfile() must succeed at tests/test_stdio_validation.c:55。设备 /tmp 为 root-owned 且用户不可写；用户可写 TMPDIR 仍不能改变 libc tmpfile 行为。最终用 CMake DISABLED 显式跳过一项，不删除测试源码、不伪造全绿。

## 消费者测试

test_package/test_blosc2.c 真实调用 blosc2_init/destroy、blosc2_compress/decompress 1024 字节 round-trip 和 blosc2_compcode_to_compname，共 1 个消费者程序、4 个断言。

## 路径与知识

- 适配路径：A
- 路径 B：不新增条目；qsort_r 根因和方案已由 E531 及 c-blosc2 先例覆盖，本任务复用并验证 FetchContent 场景。
- 已有知识：E531


---

**编译结束**: 2026-09-07 14:00
**最终状态**: built
