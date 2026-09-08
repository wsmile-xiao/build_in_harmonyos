# boost1.84-coroutine 1.84.0 适配笔记

## 编译环境
- 构建系统: custom（手动编译 + ASM 汇编，绕过 b2）
- 编译日期: 2026-09-05
- 编译器: clang 15 (OHOS SDK /data/service/hnp/bin/clang++)
- 状态: built

## 组件定位
Boost 1.84.0 组件拆分包之一：**Boost.Coroutine**（已弃用， successor 为 coroutine2；但仍被部分旧项目依赖）。提供 `boost::coroutines::asymmetric_coroutine` / `symmetric_coroutine` 协程模板及栈分配器。供下游以 `boost1.84-coroutine/1.84.0` 精确依赖该组件，不必拉取 boost/1.84.0 聚合包。

## 编译步骤
1. 下载官方源码 boost_1_84_0.tar.gz（sha256 a5800f40...5724，与 boost/1.84.0 同源）
2. 应用补丁 0001-ohos-pthread-cancel-fix.patch：boost/core/detail/sp_thread_sleep.hpp 增加 BOOST_SP_NO_PTHREAD_SETCANCELSTATE 特性宏守卫（OHOS musl 无 pthread_setcancelstate）
3. 手动编译 Boost.Context fcontext（B2 在 OHOS 不兼容，E068）：
   ```
   clang++ -std=c++17 -stdlib=libc++ -fPIC -O2 -DNDEBUG \
     -DBOOST_ALL_NO_LIB -DBOOST_CONTEXT_SOURCE -DBOOST_CONTEXT_STATIC_LINK \
     -I<boost_root> -c libs/context/src/asm/make_arm64_aapcs_elf_gas.S -o make.o
   clang++ ... -c libs/context/src/asm/jump_arm64_aapcs_elf_gas.S -o jump.o
   clang++ ... -c libs/context/src/asm/ontop_arm64_aapcs_elf_gas.S -o ontop.o
   clang++ ... -c libs/context/src/posix/stack_traits.cpp -o stack_traits_ctx.o
   llvm-ar rcs libboost_context.a make.o jump.o ontop.o stack_traits_ctx.o
   ```
   OHOS aarch64 对应 `arm64_aapcs_elf_gas`（与 Linux 相同：binary_format=elf, ABI=aapcs, assembler=gas）；clang 直接处理 .S，无需 -x assembler-with-cpp。

4. 手动编译 Boost.Coroutine：
   ```
   clang++ ... -DBOOST_COROUTINE_SOURCE -DBOOST_COROUTINES_SOURCE \
     -c libs/coroutine/src/detail/coroutine_context.cpp -o coroutine_context.o
   clang++ ... -c libs/coroutine/src/exceptions.cpp -o exceptions.o
   clang++ ... -c libs/coroutine/src/posix/stack_traits.cpp -o stack_traits_coro.o
   llvm-ar rcs libboost_coroutine.a coroutine_context.o exceptions.o stack_traits_coro.o
   ```
5. package(): 复制全量 boost/ 头文件 + libboost_context.a + libboost_coroutine.a

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | b2 构建失败 | Boost.Build SHELL 执行机制与 OHOS shell 不兼容（E068） | 手动编译 Context ASM + Coroutine 源文件（上述 7 个翻译单元） |
| 2 | sp_thread_sleep.hpp 报 pthread_setcancelstate 未声明 | OHOS musl 不实现该 API | 复用 boost/1.84.0 已验证补丁：特性宏 BOOST_SP_NO_PTHREAD_SETCANCELSTATE 守卫（R8 合规，非平台宏） |
| 3 | Context ASM 汇编失败 | 单架构多变体，OHOS aarch64 需确认 binary format/ABI | 选用 `arm64_aapcs_elf_gas.S`（Linux 同款)，实测 OHOS clang 可直接汇编 |
| 4 | coroutine 测试需 boost_unit_test_framework | 未编译 boost_test 库 | 将 `unit_test.hpp` 替换为 `included/unit_test.hpp` 单头全实现（同一套用例与断言） |

## 源码修改
- patches/0001-ohos-pthread-cancel-fix.patch（与 boost/1.84.0 同一补丁，portability 类型）

## 依赖版本
- 无外部 conan 依赖（context/coroutine 仅依赖 boost 头自身 + libc）

## 验证结果

```bash
# 上游测试（2 项，绕过 b2 手动驱动，included boost.test）
clang++ test_asymmetric_coroutine.cpp -lboost_coroutine -lboost_context && ./a.out  # PASS
clang++ test_symmetric_coroutine.cpp  -lboost_coroutine -lboost_context && ./a.out  # PASS
# 结果: 2 passed / 0 failed

# test_package（conan create 内执行 ctest）
# asymmetric coroutine pull/push 数值传递 + 迭代器 + 异常捕获 + 对称协程 yield/call + 栈分配器 + protected_stack_allocator → PASS
```

## 注意事项
- package_type = static-library；R26 系统同名检查通过（libboost_coroutine / libboost_context 非 OHOS 系统库名）
- cmake_file_name 用 Boost（与聚合 boost 包的 Boost config 兼容），组件 cmake target 为 Boost::coroutine / Boost::context
- 头文件全量安装，下游无需再装 boost 头
- Boost.Coroutine 已弃用（被 coroutine2 取代），但为兼容旧项目保留；推荐新项目使用 boost1.84-coroutine2（如后续拆分）

---

**编译结束**: 2026-09-05
**最终状态**: built
