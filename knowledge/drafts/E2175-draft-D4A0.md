# E2175 — 上游多线程模式测试在 musl/OHOS 必现 SIGSEGV 时改用上游官方便携（单线程）模式开关

## 错误特征
```
cl_test 运行中随机 SIGSEGV（"timeout: the monitored command dumped core"），
崩溃套件在 Atomic Updates（TestThreading）/ IndexWriter / Query Parser 间漂移；
同源码 Debug(-O0) 与 Release(-O3) 同崩，ENABLE_MMAP=OFF 不影响；
部分轮次表现为 IndexSearcher 套件挂起（条件变量丢唤醒类时序）。
```

## 触发条件
- 构建系统: cmake（上游 OPTION(DISABLE_MULTITHREADING ...) 未显式关闭时默认 MT 开启）
- 阶段: testing（上游自带线程压力测试，如 CLucene TestThreading 的
  "1 writer + 2 search 线程并发读写"套件）
- 平台: musl libc（OHOS）+ clang；glibc 桌面发行版历史上可因调度时序侥幸通过

## 根因分析
上游 MT 代码存在真实数据竞争缺陷（如 CLucene FSDirectory 的
FSIndexInput::close 对 `dounlock` 分支处理错误：refcount=1 时先
`delete mutex` 而其他线程仍可能持锁等待；另有条件变量通知不持锁
导致的丢唤醒窗口）。这些竞争在 glibc 时序下常被掩盖；musl 的调度
与内存序行为使其必现。上游同时提供了官方便携开关
`OPTION(DISABLE_MULTITHREADING ...)`（单线程模式，pthread 分支整体
不编入、同步原语退化为直调/空操作），但该模式的支撑宏自老版本起
位腐烂（缺 `_LUCENE_ATOMIC_INT_SET/GET`、`mutex_thread` 空实现、
`Misc::toString(threadid)` 未加条件编译），直接编译失败。
musl 生态先例：Adélie 的 disable-threading 补丁、chimera 的
multithreading.patch + 模板注释 "tests fail with mt enabled"。

## 解决方案

### 推荐方案
1. 以 `cmake -DDISABLE_MULTITHREADING=ON` 走上游官方便携模式；
2. 补齐该模式缺失的宏/桩（参照 chimera multithreading.patch：
   LuceneThreads.h 单线程分支补 `_LUCENE_ATOMIC_INT_SET/GET`、
   `mutex_thread{lock,unlock}` 空实现与 `DEFINE_MUTEX`/`STATIC_DEFINE_MUTEX`；
   Misc.cpp/.h 的线程 id toString 加 `#ifndef _CL_DISABLE_MULTITHREADING`）；
3. 全量重跑上游测试（而非仅跑变更用例），确认 100% 通过后在
   notes/manifest/PR 显著声明单线程语义边界。

### 禁止做法
- ❌ 保留 MT 开启仅排除/跳过崩溃的线程套件（上游测试默认必须全通过）
- ❌ 用 `__OHOS__` 条件编译改写上游 MT 逻辑（R8：优先上游既有开关）

## 验证
```bash
cmake -DDISABLE_MULTITHREADING=ON .. && make cl_test
cd build/src/test && TEMP=test-tmp TMP=test-tmp ../../bin/cl_test
# 预期：159 tests run: 159 passed, 0 failed（clucene-core 2.3.3.4 实测 3 轮一致）
```

## 关联条目
- 相关: E187（CMAKE_POLICY_VERSION_MINIMUM 政策参数，同一适配中的
  CMake 4 兼容手段）
