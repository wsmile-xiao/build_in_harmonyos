# notcurses 3.0.17 编译进度

**日期**: 2026-04-16 (更新: 2026-09-17)
**状态**: ✅ built (v3: R8 特性检测重构 + 协作式线程收尾)

## 步骤记录

| 步骤 | 状态 | 备注 |
|------|------|------|
| Step 1 init | ✅ | CMake 配置完成 |
| Step 2 patches | ✅ | 10 个补丁（v3 重构，编号见 conandata.yml） |
| Step 3 configure | ✅ | cmake 成功 |
| Step 4 make | ✅ | make -j$(nproc) 成功 |
| Step 5 install | ✅ | make install → ~/usr/local/ |
| Step 6 safety | ✅ | 安全弹窗已通过 |
| Step 7 check | ✅ | 验证程序 timeout 5 EXIT=0 |
| Step 8 staging | ✅ | 预编译包制作完成 |
| Step 9 package | ✅ | tar.gz + install.sh |
| Step 10 deploy | ✅ | 本地安装验证 |
| Step 11 finish | ✅ | 归档完成 |

## 发现与知识

### v2 更新（2026-04-17）：终端查询细化

**问题**：v1 版本完全跳过了 `send_initial_queries()`，导致 SMCUP（进入备选屏幕）和 KKBDENTER（键盘初始化）都没有发送，终端没有进入备选屏幕模式，键盘无法正常工作（不能输入/回车）。

**修复**：细化 `send_initial_queries()` 补丁，只跳过需要响应的查询（DA1/DA2/DSRCPR/DIRECTIVES），保留不需要响应的初始化序列（SMCUP/KKBDENTER）。

### 关键经验

1. **SMCUP 必须发送**：否则终端不进入备选屏幕模式
2. **KKBDENTER 应该发送**：初始化键盘协议，否则键盘可能不响应
3. **DA1/DA2/DSRCPR 必须跳过**：OHOS 终端不响应，会导致 `pthread_cond_wait` 永久阻塞（经 `NOTCURSES_TERM_QUIRKS` 选项控制）
4. **`pthread_cancel` 不可用**：OHOS libc 无此符号，线程收尾一律协作式关闭（stop 标志 + 唤醒 + join + 释放）
5. **`ppoll`/`mremap` 头文件不可见**：无 `_GNU_SOURCE` 时不被 musl 头声明（`check_symbol_exists` 探测结果与编译上下文一致），回退 `poll`/`realloc`
### v3 更新（2026-09-17）：AI 检视意见闭环（R8/R39/P1 修复）

**R8（平台宏）系统性重构**：移除全部 `__OHOS__` 平台条件编译，改为配置期特性检测 + 构建选项（AI 检视多轮意见，逐条修复）：
- `0001` CMakeLists 新增 `check_symbol_exists` 探测 `HAVE_PTHREAD_CANCEL` / `HAVE_PPOLL` / `HAVE_MREMAP`（设备实测：OHOS libc 头文件不声明 pthread_cancel/ppoll/mremap；pthread_cancel 符号亦缺失；ppoll/mremap 符号存在但需 `_GNU_SOURCE` 才声明，而 notcurses-core 仅在 `CMAKE_SYSTEM_NAME STREQUAL "Linux"` 时定义 `_GNU_SOURCE`，OHOS 映射为 HarmonyOS 故不可见）+ `NOTCURSES_TERM_QUIRKS` 选项（终端行为怪癖：跳过无响应查询、合成 Enter 处理）
- `0004` fbuf.h：`#ifdef __linux__` → `#ifdef HAVE_MREMAP`（mmap/mremap/munmap ↔ malloc/realloc/free 家族保持分配纪律一致）
- `0006` in.c：ppoll 分支由 `!defined(HAVE_PPOLL)` 选择（上游 APPLE/MINGW 同款 poll 路径）
- `0009/0010/0007`：`__OHOS__` → `NOTCURSES_TERM_QUIRKS`（终端行为差异属运行时语义，无法特性检测，按检视建议经构建选项注入，conanfile 在 os=OHOS 时开启）

**P1 修复：stop_input() 死锁（demo/input.c）**：原 OHOS 路径先 `pthread_join` 后 `close(pipe)`，而线程阻塞在 `notcurses_get_blocking()` 的条件变量上（并非读管道——检视建议的"先关管道"无法唤醒它）。重构为协作式退出：`notcurses_get_nblock()` + 50ms 轮询 + `input_stop_requested` 标志，`stop_input()` 置标志后 join 立即返回。

**P1/P2 修复：stop_inputlayer() 内存泄漏（lib/in.c）**：原 detach 方案泄漏 inputctx（含管道/mutex/initdata）且 fd 状态仅部分恢复。改为协作式关闭：`ictx->stopping` 标志 + 有界 poll 超时（100ms 重检）+ `pthread_kill(SIGWINCH)` 加速唤醒 + `pthread_join` + `set_fd_nonblocking` + `free_inputctx`——无泄漏、无残留 detach 线程。

**P2 修复：kill_tablet() 潜在挂起（demo/reel.c）**：tablet_thread 死循环依赖 cancel 终止。加 `stop` 标志 + SIGWINCH 打断 nanosleep，join 快速返回。

**P2 修复：ncfdplane_destroy() 潜在死锁（lib/fd.c + internal.h）**：无 cancel 时 follow 模式 fd 永不 EOF → join 挂起。fdthread 增补 stoppipe 轮询，destroy 写管道唤醒后 join（donecb 在该路径抑制，与上游 cancel 语义一致）；ncsubproc_destroy 依赖 SIGKILL 后管道 EOF 使线程退出（孙进程持有管道的极端场景为已知限制，注释说明）。

**P1 修复（W4 审计 R40）：test_package 功能级验证 + 光标报告超时**：
- 深挖 pty 冒烟测试时发现 `get_cursor_location()`（in.c）对光标报告（ESC[6n/CPR）**无限期** `pthread_cond_wait` —— 不响应查询的终端上 `notcurses_init` 会永久挂死（旧补丁同样存在，只是此前未被发现）。已改为 `pthread_cond_timedwait` 250ms 有界等待，超时优雅降级（光标位置不可用，init 继续），并重置 `coutstanding` 允许下次重试。该修复对所有平台生效（健康终端 CPR 响应 <10ms，超时永不触发）。
- test_package 重写为两部分：① `notcurses_version()` API/版本断言；② **pty 功能循环**（openpty → notcurses_init → 渲染 → 注入 'q' 按键经输入层取回 → notcurses_stop）——端到端验证 OHOS 适配核心（查询跳过/有界等待、输入线程、协作式关闭无死锁）。TERMINFO 由 test conanfile 从 ncurses 包注入（conanrun env），CI 无头环境可运行。

**R39**：conandata.yml 仅保留官方 GitHub URL（gh-proxy 镜像已于 2026-08-30 移除，CI 自动加镜像 fallback；本地 W3 模拟的 build_and_test.sh 会临时改写工作区 conandata.yml 且此版本脚本不还原——提交前需核对，已从 .orig 恢复）。

**cancel_and_join 语义（internal.h）**：无 `HAVE_PTHREAD_CANCEL` 时退化为 join-only，所有调用方（in.c/fd.c/gpm.c）已逐一核对其线程可自行退出。
---

**编译结束**: 2026-09-17 13:29
**最终状态**: built
