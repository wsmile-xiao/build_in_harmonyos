# rtags 2.44 适配笔记

## 编译环境
- 构建系统: CMake + Ninja（真机原生编译）
- 编译日期: 2026-10-03
- 编译器: /data/service/hnp/bin/clang++（clang 15 wrapper，cppstd=17, libc++）
- 依赖: clang/22.1.8（conan 制品仓 ohpcd，含 libclang + llvm-config）
- 状态: built（conan create 全链路 + test_package 功能测试通过）

## 编译步骤
1. 双官方源：上游 v2.44 tarball + rct submodule pinned commit（9121fb0）解压到 src/rct
2. `-DLIBCLANG_ROOT_DIR=<clang包>` + `-DLIBCLANG_LLVM_CONFIG_EXECUTABLE=<clang包>/bin/llvm-config`
3. package() 内 binary-sign-tool 签名（`sign -inFile f -outFile f -selfSign 1`）+ llvm-objcopy 清 .codesign
4. test_package：rc --version smoke → rdm --tcp-port 启动 → rc -J 装载 compile_commands.json 索引 → rc -T 等待 → rc -R 引用查询断言

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure_file 拼路径报错 | 上游用 `${CMAKE_MODULE_PATH}/Uninstall.cmake.in`，CMAKE_MODULE_PATH 为列表 | 0001 改 `${PROJECT_SOURCE_DIR}/cmake/...` |
| 2 | MemoryMonitor #error | rct 平台宏 OS_<CMAKE_SYSTEM_NAME> 在鸿蒙PC 上无对应分支 | 0002 用编译器内建 __linux__ 探测（OHOS clang 有定义），走 /proc/self/smaps |
| 3 | pthread_cancel 链接 undefined symbol | OHOS musl 未导出 pthread_cancel | 0002 rct.cmake check_symbol_exists 构建期探测生成 RCT_HAVE_PTHREAD_CANCEL，无符号时析构兜底 pthread_detach |
| 4 | rdm "Failed to listen on ~/.rdm (errno 1)" | SELinux 禁止 AF_UNIX bind（全目录） | 0003 --tcp-port 时降级 TCP-only |
| 5 | isCompiler mkstemp /tmp errno 30 | 鸿蒙PC /tmp 只读 | 0004 改用 TMPDIR |
| 6 | "indexing crashed / Failed to connect to rdm on ~/.rdm" | rp 回连仍用 unix socket | 0005 ClangIndexer 支持 tcp@host:port + 0003 改写 socketFile |
| 7 | rc -c exit 1 无输出 | project root 无标记 | 测试内写 compile_commands.json（rc -c/-J 均依赖） |
| 8 | binary-sign-tool sign 报 COMMAND_PARAM_ERROR | 参数语法不同 | 用 `sign -inFile f -outFile f -selfSign 1` |

## 源码修改
全部通过 patches/0001~0005 沉淀（conandata.yml patches 自动应用），无未记录修改。

## 功能测试结论
rdm/rc/rp 在鸿蒙PC 完整可用：libclang 解析、索引入库、符号引用查询均通过；唯一平台差异是 IPC 必须走 TCP 回环而非 unix socket。

## 关闭

## 检视意见核验（PR #14417 第二轮，2026-10-04）

1. **conandata.yml rct tarball sha256 与 manifest.yaml 不一致（P2）**：
   真实下载件裁决——`curl https://codeload.github.com/Andersbakken/rtags/tar.gz/refs/tags/v2.44`
   后 `sha256sum` 实测为 `4343df5d4d3fefb01d28bed209c27ba2a15f55a3a7437bf06b225e73ef70b521`，
   与 conandata.yml 一致；**manifest.yaml 第 41 位系笔误（a3→f3），已修正**。

2. **无 pthread_cancel 平台析构兑底 pthread_join 可能无限阻塞（P2）**：逐个人工核验 rct 全部
   Thread 子类（Thread.h 唯一基类，子类仅 3 个），均可在停止信号后自然退出 run()，
   且正规析构路径都先 stop/join 再 delete，析构兑底 join 仅为异常路径兑底：
   - `MessageThread`（MessageQueue.cpp）：`stop()` 退出事件循环；`MessageQueue` 三个删除点均为 stop()+join() 后 delete；
   - `ThreadPoolThread`（ThreadPool.cpp）：run() 在 `mStopped` 时 break；`ThreadPool` 两处清理（126-127、149-150 行）均 stop()+join() 后 delete；
   - `ProcessThread`（Process.cpp）：run() 从 `sProcessPipe[0]` read 到 `'s'`（wakeup(Stop)）后 break；`ProcessThread::shutdown()`（245-249 行）wakeup(Stop)+join() 后 delete。
   结论：正常路径析构兑底 join 不会执行，不存在关闭期挂死风险；仅在调用方遗漏 join 的异常场景
   兑底等待线程自然退出，这是无 pthread_cancel 平台上防 UAF 的唯一安全选择（pthread_detach 会导致
   线程继续访问已析构对象），风险可接受。

## 关闭

最终状态: status: closed COMPLETED
rtags 2.44 鸿蒙PC aarch64 适配完成（built）：conan create 全链路 + test_package 功能测试（索引+引用查询）通过，
制品与测试报告归档于 packaging/ 与 reports/。编译结束。
---

**编译结束**: 2026-10-03 09:28
**最终状态**: built
