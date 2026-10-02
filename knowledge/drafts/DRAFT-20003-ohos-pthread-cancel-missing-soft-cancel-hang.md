# DRAFT-20003: OHOS pthread_cancel 缺失 → 硬取消分支编译必炸 + 软取消关闭路径非确定性挂起

- 条目主题：OHOS（musl）的 pthread.h 定义了 `PTHREAD_CANCEL_ASYNCHRONOUS` 等宏常量但不提供 `pthread_cancel()`/`pthread_setcanceltype()` 函数——`#ifdef PTHREAD_CANCEL_ASYNCHRONOUS` 门控的硬取消代码必编译失败；禁用硬取消后，引擎类软件的软取消关闭路径存在非确定性挂起（s_tmutex FUTEX 阻塞，进程不退出）。
- 状态：草稿（待知识库主编审核，拟提升编号 Exxx）
- 关联软件：yate 6.4.1（engine/Thread.cpp）；同范式适用于所有用 pthread_cancel 做线程终止的引擎类软件。

## 错误特征
- 编译期：`pthread_cancel was not declared in this scope` / `implicit declaration of function 'pthread_cancel'` / 链接期 undefined reference
- 运行期：`<NOTE> Soft cancelling N running threads` 之后进程挂起 >4 分钟不退出（`-Dx` init-then-exit 冒烟）
- /proc 现场：仅剩主线程，`State: S`、`wchan: FUTEX`；输出文件中无 "Hard cancelling" / "cannot terminate" 刷屏（未进入硬取消自旋，死在软循环的 s_tmutex.lock()）

## 根因
1. 宏常量与函数实现脱节：pthread.h 有 `PTHREAD_CANCEL_*` 常量（门控被选中）但 libc 无 `pthread_cancel` 符号（E051 未实现 syscall 族）。
2. 软取消依赖线程主动检查 `m_cancel` 标志到达取消点；线程阻塞在无超时的 I/O 时永不退出；线程死亡后 `s_threads` 列表条目残留/`s_tmutex` 持锁未释放 → `killall()` 软循环的主线程 `s_tmutex.lock()` 永久阻塞。
3. 非确定性：线程恰好都在取消点完成时正常退出（探索期曾 rc=0）。

## 修复 / 工程对策
1. 补丁改门控宏（`#ifdef PTHREAD_CANCEL_ASYNCHRONOUS` → `#ifdef YATE_HAVE_PTHREAD_CANCEL`，永不定义），走软取消路径——编译可过。
2. 冒烟测试用**纯 POSIX 子 shell 超时守卫**，断言功能状态而非退出码：
```sh
( "yate" -Dx -c etc -m modules -e ext > smoke.out 2>&1 & p=$!;
  ( sleep 30; kill -9 $p 2>/dev/null ) & k=$!;
  wait $p 2>/dev/null; kill $k 2>/dev/null; true; )
```
   断言 `smoke.out` 含 "Yate engine is initialized" + 目标模块名（初始化/模块加载发生在 ~1s 内，挂起只影响退出）。
3. 注意：系统 `/bin/sh` 拒绝 `VAR=x { }` 复合命令前缀（`syntax error: unexpected '}'`），守卫勿用 `VAR=` 前缀 + 花括号组；conan wrapper 经 `/bin/sh -c` 执行。
4. 平台侧：补齐 pthread_cancel（可 `req add` 登记系统能力缺口）后恢复硬取消分支。

## 验证
- yate 6.4.1：补丁后编译全绿；`-Dx` 挂起复现（2026-09-30 00:22 实测，/proc 单线程 FUTEX）；超时守卫下 test_package 5/5 断言通过。
